"""Ties burst_cycle + squad_engine + effects + damage_formula + attack_rate
into one timeline: schedules the burst rotation, fires skill triggers at the
right moments, and totals up both burst-skill damage instances and normal-
attack damage over the fight.

"Deals X% of final ATK as burst damage" (and normal attacks' own damage%)
are passed as calculate_damage's `attack_coefficient`, NOT folded into atk:
per nikke.gg's formula the coefficient multiplies the whole Base Damage
(after defense subtraction and flat-ATK additions), so pre-multiplying atk
would mis-scale defense and flat ATK. The raw summary ATK goes in as `atk`.

Normal-attack damage is computed as a separate pass after the burst-cycle
simulation finishes: burst_cycle's hooks already populate the EffectRegistry
with every buff across the whole fight (each Effect carries its own
applied_at/duration), so querying registry.total_for(stat, target, shot_time)
for a shot time anywhere in the fight is correct regardless of processing
order - no need to interleave shot generation with the burst-cycle hooks.

Core hit damage is per-caster: `core_damage.core_hit_bonus_for(slug)` reads
the caster's `shot_detail.core_damage_rate` and returns the major-modifier
term it adds, defaulting to +100% (200% total, i.e. exactly doubles a hit
with no other modifiers) with four characters at +150% (250% total) - see
that module's docstring for the table and where the rate comes from.
Fienn's direct in-game/ShiftyPad tooltip check is what pins the default -
this corrects an earlier "1/1.5" figure pulled from a summarized fetch of
the nikke.gg formula page, which turned out to be an unreliable paraphrase.
`core_hittable` toggles it for the whole simulation (some raid bosses have
an exploitable core, some don't), and `core_eligible` decides which
instances inside such a fight collect it: NORMAL ATTACKS plus `core_strike`
skill damage, never other skill damage, and never Sustained / Distributed
damage. What is still not modeled is how OFTEN a real player lands the core
- an eligible hit here always does.

reload_speed_percent and max_ammo_percent effects (from overload options or
skills) are read live from the registry at each magazine's start/reload
moment, so temporary buffs correctly speed up reloads or grow magazines
only while active - see attack_rate's docstring for exactly when each is
evaluated.

`boss_element` (optional) applies NIKKE's +10% elemental advantage to every
damage instance from an attacker whose element beats the boss's; None means
no element is considered (neutral for everyone).

Crit is modeled as expected value, not per-hit RNG: every hit's damage is
scaled by 1 + crit_rate*(0.5 + crit damage sources), where crit_rate is the
15% base plus any crit_rate buffs (capped at 100%). So crit rate AND crit
damage buffs both raise output, which is what most Burst-1 supporters exist
to do. base_crit_rate can be overridden (e.g. 0.0 in tests that want
deterministic non-crit numbers).

Known simplifications: a slug missing from `weapon_stats` contributes no
normal-attack damage (e.g. while that character's weapon data hasn't been
entered yet).

Pierce Damage Up only credits a unit that actually HAS Pierce - the skill-text
marker is [관통 특화] / "Gain Pierce" (Fienn, 2026-07-26). Pierce is carried as
its own registry stat `has_pierce`, so a unit that gains it for 5 sec is
credited for exactly those 5 sec, and a squad-wide Pierce Damage buff does
nothing for allies who never gain the property.

Some passives "Deal X% of final ATK as damage" on a trigger OTHER than the
caster's own burst (e.g. Brid: Silent Track's Ignition Sequence, which fires
on full_burst_enter regardless of who bursts) - this can't use
`burst_damage_percents`, which is tied to `own_burst_activate`. A skill rule
emits an `"instant_damage_percent"` Pulse instead (see
`_helpers.instant_nuke_pulse_rule`); `drain_instant_damage` drains it after
every trigger fire (battle_start, own_burst_activate, full_burst_enter,
full_burst_end) and computes the damage the same way as a burst nuke, using
the pulse's source_slug as caster. Logged with `source="instant_nuke"`.

Some skills react to a DIFFERENT unit's burst (e.g. Prika's Encore fires when
Mint's Sing Along takes effect - i.e. when Mint bursts). After a unit's burst
tier fires, `on_tier_fire` records the bursting slug on the context
(`last_burst_slug`) and fires an `ally_burst_activate` trigger across every
unit's rules, so a reacting rule can gate on `ally_bursted("mint")`. Fired after
the burster's own own_burst_activate, so the reacting rule sees the burst's own
effects already applied. These rules must be buff appliers (no instant nukes),
like periodic_rules.

Some skills fire repeatedly on their OWN fixed cooldown, entirely independent
of the burst cycle and every other trigger (e.g. Helm: Aquamarine's Aegis
Cannon Suppression Fire, a "Cooldown: 4s" active skill separate from her
Burst tab, that auto-fires throughout the whole fight). `periodic_nukes` is a
`{slug: {"cooldown": seconds, "percent": float}}` map; each entry ticks at
t=cooldown, 2*cooldown, ... up to fight_duration, computing damage the same
way as a burst nuke (using the tick time to read live buffs, so it correctly
reflects whatever's active at that instant). Logged with `source="periodic"`.
Every tick computes at its OWN time, so a tick landing inside a Full Burst
window collects the bonus and one outside does not - no per-spec opt-in, see
`_damage_instance`.
A spec may also carry `"during_full_burst": True` (ticks only inside each
Full Burst window, anchored to the window's start - gap #6), `"hit_count": N`
(each tick records N separate hits, same rationale as burst_hit_counts), and
`"own_burst_interval": (interval, duration)` (a window whose start falls
inside [own burst, +duration) ticks at `interval` instead of `cooldown`).
Defaults keep every existing spec identical.
Computed as a pass after the burst-cycle simulation completes, same as the
normal-attack pass - order doesn't matter since it only reads the registry's
already-populated Effects at arbitrary times, like every other post-pass here.

Both `periodic_nukes` values and `resource_scaled_nukes` specs may carry an
optional `"requires_part_destructible": True | False` to fire only on one
side of a boss-profile flag (e.g. Ark Ranger Black's floor DoT vs. ceiling
DoT modeling the same battery-transformation state two different ways);
absent field = always fires, matching every existing spec's behavior.
"""
import inspect
import warnings
from dataclasses import replace

from app.accuracy import WEAPON_SPREAD_DIAMETER, core_hit_rate
from app.attack_rate import AmmoRefill, CHARGE_WEAPONS, generate_segmented_shots
from app.burst_cycle import FULL_BURST_OPEN_DELAY, simulate_burst_cycle
from app.core_damage import core_hit_bonus_for
from app.damage_formula import calculate_damage
from app.effects import Effect, EffectRegistry, _matches_scope, max_ammo_percent_total
from app.elements import ELEMENT_ADVANTAGE_BONUS, element_multiplier
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# How far past a window's end an "after this window ends" event is placed, so
# it orders after anything landing on the boundary instant itself.
AFTER_WINDOW_EPSILON = 1e-3

BASE_CRIT_RATE = 0.15

# 스킬 쿨다운 감소의 하한 배수. 감소가 100%에 닿으면 주기 루프가 전진하지 않는다.
# 오늘 데이터로는 스킬 쿨감을 주는 유닛이 아르카나 하나뿐이라(75%) 겹칠 수 없고,
# 그래서 합산 규칙이 가산인지 승산인지는 알 수 없다 - 이 상수는 그 규칙이 아니라
# 무한 루프 방어다.
MIN_COOLDOWN_FACTOR = 0.05

# Damage types that can never hit a core, whatever fired them.
NON_CORE_DAMAGE_TYPES = frozenset({"sustained", "distributed"})

# Which weapons are inside their effective range at each distance a boss can be
# fought at (Fienn, 2026-07-28). The band belongs to the ENCOUNTER, the weapon
# list to the game: Annihilio is a mid-range fight, so its AR and MG collect the
# bonus and nothing else does (Fienn, 2026-07-31).
#
# A Rocket Launcher appears in no band. Anis: Star's range footage reads a
# non-crit normal attack's major bucket as exactly 1.000000 outside Full Burst
# and 1.500000 inside - no range term anywhere - where a weapon that could
# collect it would land on 1.30/1.80. That makes an RL the measuring stick for
# the rest of the bucket rather than a unit standing in the wrong place.
EFFECTIVE_RANGE_BANDS = {
    "near": frozenset({"SG", "SMG"}),
    "mid": frozenset({"AR", "MG"}),
    "far": frozenset({"SR"}),
}


def resolve_ammo_refunds(weapon, boss_element):
    """Every ammo refund this unit actually gets against THIS boss.

    Two sources, and a unit can hold both: the Tactical Bear cube's, which its
    wearer gets in any encounter, and one off her own skill, which may require
    a boss element (EVE's Eagle Eye-Type Exospine reloads only "on an Electric
    Code target"). `roster` cannot resolve the second - it assembles a deck, not
    an encounter - so it carries the requirement here as
    `("skill_ammo_refund", (refund, element or None))`.
    """
    refunds = []
    cube = weapon.get("ammo_refund")
    if cube is not None:
        refunds.append(cube)
    skill = weapon.get("skill_ammo_refund")
    if skill is not None:
        refund, required_element = skill
        if required_element is None or required_element == boss_element:
            refunds.append(refund)
    return tuple(refunds)


def resolve_ammo_refund_windows(slug, events):
    """[this slug's own burst, that cycle's Full Burst end) for every cycle
    its own burst fires.

    Arcana: Fortune Mate's reload rotation counts only the normal attacks she
    lands while Making Memories is up, and "Resets when Making Memories is
    removed" - the Full Burst end that clears it (`clear_making_memories`).
    Reading the end off the event log rather than a fixed constant keeps her
    window honest in a deck whose Burst 3 moves Full Burst's length (Isabel
    -5 sec, Modernia +5 sec) - the same reasoning the rotation's OTHER two
    phases already use via `per_shot_cycle_from_own_burst_to_full_burst_end`.
    Every "burst" event `simulate_burst_cycle` emits is followed by its own
    "full_burst_start"/"full_burst_end" pair in that same iteration (the loop
    only breaks BEFORE firing a cycle whose bursts would land at or past
    `fight_duration`), so a real event log never leaves one unclosed.
    """
    windows = []
    for event in events:
        if event["type"] != "burst" or event["slug"] != slug:
            continue
        end = next((e["time"] for e in events
                    if e["type"] == "full_burst_end" and e["time"] > event["time"]),
                   None)
        if end is not None:
            windows.append((event["time"], end))
    return tuple(windows)


def resolve_ammo_refills(deck, events):
    """Every timed ammo refill each deck member receives, by slug.

    A grant names its trigger as an event the burst cycle logs - "when entering
    Full Burst" (Noir) or the caster's own burst (Little Mermaid, Asuka, Arcana)
    - and its scope as self or the whole squad. Resolving it here rather than in
    the roster is the same split the boss-element gate on skill refunds uses:
    the roster assembles a deck and does not know the encounter.
    """
    refills = {}
    for member in deck:
        grant = member.get("ammo_refill_grant")
        if not grant:
            continue
        if grant["event"] == "full_burst_enter":
            times = [e["time"] for e in events if e["type"] == "full_burst_start"]
        else:
            times = [e["time"] for e in events
                     if e["type"] == "burst" and e["slug"] == member["slug"]]
        if not times:
            continue
        recipients = ([m["slug"] for m in deck] if grant["scope"] == "squad"
                      else [member["slug"]])
        for slug in recipients:
            refills.setdefault(slug, []).extend(
                AmmoRefill(time=t, rounds=grant.get("rounds", 0),
                           percent=grant.get("percent", 0.0))
                for t in times)
    return {slug: tuple(sorted(items, key=lambda r: r.time))
            for slug, items in refills.items()}


def core_eligible(source, damage_type):
    """Whether a damage instance can collect the Core Damage bonus.

    Core Damage is a NORMAL-ATTACK-only modifier: skill damage - burst nukes,
    per-shot riders, DoTs, scheduled ticks - never collects it, and Sustained /
    Distributed damage cannot hit a core at all even when it IS the unit's
    normal attack (Fienn, in-game, 2026-07-26). Every source in the damage log
    other than "normal_attack" is skill damage.

    "Core strike damage" (코어 명중 대미지) is the named exception, and it is a
    skill damage type by construction. Its in-game tooltip: it strikes the
    target's BODY rather than a real core part, but "is displayed as core
    damage, and the core bonus multiplier and core-damage up/down effects
    apply" - so it collects exactly what a core hit collects. The same tooltip
    says it does NOT fire "on core hit" conditions; nothing to guard, as this
    engine has no core-hit trigger (Fienn, 2026-07-26).

    A SUMMON is the second exception, and it is not a damage type but a per-
    instance fact, so a `scheduled_nukes` spec opts in with `core_eligible`
    rather than being decided here: Anis: Star's Shooting Stars are stars that
    aim and shoot on their own, and in game their damage lands as core hits
    (Fienn, range footage 2026-07-28). "Scheduled tick" describes how the engine
    emits the damage, not what the game thinks it is - a summon's shot is a
    normal attack, just not its owner's.
    """
    if damage_type == "core_strike":
        return True
    return source == "normal_attack" and damage_type not in NON_CORE_DAMAGE_TYPES

# A `burst_anchored_buffs` duration meaning "hold until this unit's next own
# burst" (a state a burst enters and only the next burst clears), as opposed to
# a fixed number of seconds.
UNTIL_NEXT_OWN_BURST = "until_next_own_burst"


def _expected_crit_positions(times, threshold, crit_rate_at):
    """Indices into `times` where a running total of EXPECTED critical hits
    crosses `threshold`, carrying the remainder forward.

    Crit is expected value in this engine (every hit's damage is scaled by the
    crit factor; no per-hit roll), so "after N critical hits" has no event to
    count. It is instead converted the same way the damage path converts crit:
    each shot contributes the unit's LIVE crit rate at that instant. Reading the
    rate per shot rather than folding a fixed `N / crit_rate` shot count at
    build time is what makes an ally's crit buff genuinely speed the trigger up
    (Fienn's condition for accepting the conversion, 2026-07-20).

    Shared by `per_shot_rules`' "every_n_critical_hits" mode (EVE's Unstable
    Energy) and the "per_critical_hit_every" resource fill (Julia's signature
    Crescendo) so the two cannot drift apart.

    The `1e-9` is load-bearing, not cosmetic: summing a rate like 0.3 ten times
    lands on 2.9999999999999996, which would push a proc a whole shot later
    than exact arithmetic puts it.
    """
    positions = []
    accumulated = 0.0
    for index, time in enumerate(times):
        accumulated += crit_rate_at(time)
        if accumulated + 1e-9 >= threshold:
            positions.append(index)
            accumulated -= threshold
    return positions


def _resource_fill_times(
    fill, shot_times, core_hittable, fight_duration, full_burst_windows=(), own_burst_times=(),
    last_bullet_times=(), crit_rate_at=None,
):
    """The times a resource gains a stack, from its fill spec and the owner's
    shot timeline. ("computed", fn) hands the walk to the owning module, for a
    resource whose sources interact (see that branch below); every other kind is
    declarative. ("per_shot_every", N) fires at the owner's Nth, 2Nth, ... shot
    (count = index+1, matching per_shot_rules' "every N").
    ("per_shot_every_core", core_n, noncore_n) picks core_n on a core-hittable
    boss and noncore_n otherwise - for a skill whose fill rate differs between
    hitting the core and not (e.g. Guillotine's EXP). ("periodic", interval)
    fires at t=interval, 2*interval, ... up to fight_duration, independent of
    the owner's shots (e.g. Cinderella's Beautiful, which ticks on a fixed timer
    while her decoy is up from battle start). ("per_shot_every_during_full_burst",
    N) is like "per_shot_every" but counts only shots whose time falls within a
    Full Burst window (e.g. Soda's Golden Chip, "every 3 normal attacks during
    Full Burst") - shots outside any window are dropped before the "every Nth"
    count, not just skipped in place. ("per_shot_every_during_own_status_window",
    N, window_duration) is the same idea but the window is anchored to the
    OWNER'S OWN burst-fire times instead of the global Full Burst window (e.g.
    Asuka's Anti A.T. Field, "every 10 shots while in Annihilation State" - a
    9s window that starts at HER burst, not the squad's Full Burst window).
    ("per_shot_every_outside_own_status_window", N, window_duration) is its
    mirror - shots that fall OUTSIDE that window (e.g. Laplace's Hero Vision,
    fed by Full Charge attacks and so blind to her own Buster transform ticks).
    ("on_last_bullet",) fires whenever the owner's OWN shot empties its
    magazine (e.g. Julia's Crescendo, "when the last bullet hits the target"
    - see `attack_rate.last_bullet_shot_times`), not on any fixed shot count
    or window."""
    kind = fill[0]
    if kind == "computed":
        # ("computed", fn): the owning module walks the shot timeline itself and
        # hands back the fill times. For a resource whose sources INTERACT -
        # where one source's next fill depends on when the resource was last
        # spent - the per-source schedules the kinds below produce cannot be
        # merged after the fact, because they are not independent. Phantom's
        # Thief's Dagger is the case: spending it strips Calling Card, which is
        # the very condition re-arming the other source.
        #
        # Only reach for this when the interaction is real. A resource whose
        # sources are independent belongs on the declarative kinds, which the
        # engine can reason about (and which no unit can get subtly wrong).
        return list(fill[1](shot_times))
    if kind == "per_critical_hit_every":
        # ("per_critical_hit_every", N): a stack per N EXPECTED critical hits
        # with normal attacks - Julia's signature Crescendo. Unlike the
        # per-shot kinds this needs the owner's live crit rate, so the caller
        # supplies `crit_rate_at`; see `_expected_crit_positions`.
        n = fill[1]
        return [shot_times[i] for i in _expected_crit_positions(shot_times, n, crit_rate_at)]
    if kind == "per_shot_every":
        n = fill[1]
        return [t for i, t in enumerate(shot_times) if (i + 1) % n == 0]
    if kind == "per_shot_every_core":
        n = fill[1] if core_hittable else fill[2]
        return [t for i, t in enumerate(shot_times) if (i + 1) % n == 0]
    if kind == "periodic":
        interval = fill[1]
        ticks = []
        tick = interval
        while tick <= fight_duration:
            ticks.append(tick)
            tick += interval
        return ticks
    if kind == "per_shot_every_during_full_burst":
        n = fill[1]
        in_window = [t for t in shot_times if any(start <= t < end for start, end in full_burst_windows)]
        return [t for i, t in enumerate(in_window) if (i + 1) % n == 0]
    if kind == "per_shot_every_during_own_status_window":
        n, window_duration = fill[1], fill[2]
        windows = [(bt, bt + window_duration) for bt in own_burst_times]
        in_window = [t for t in shot_times if any(start <= t < end for start, end in windows)]
        return [t for i, t in enumerate(in_window) if (i + 1) % n == 0]
    if kind == "per_shot_every_outside_own_status_window":
        # The mirror of the kind above: counts only shots OUTSIDE a status the
        # owner's own burst opens (e.g. Laplace's Hero Vision, fed by Full
        # Charge attacks - during her Buster transform her weapon is not a
        # charge weapon at all, and those transform ticks sit in `shot_times`
        # alongside her ordinary shots).
        #
        # This is not the same filter as "outside Full Burst": the two windows
        # start together but need not END together (a 5-sec transform inside a
        # 10-sec Full Burst), and the shots between the two ends are genuine
        # owner shots that must still count.
        #
        # Closed on both ends, like `per_shot_every_outside_full_burst`: a shot
        # landing exactly on a boundary belongs to the status window, so which
        # side of a float boundary a coincident shot rounds to cannot change
        # the count (the last transform tick nominally at burst+duration).
        n, window_duration = fill[1], fill[2]
        windows = [(bt, bt + window_duration) for bt in own_burst_times]
        out_of_window = [
            t for t in shot_times if not any(start <= t <= end for start, end in windows)
        ]
        return [t for i, t in enumerate(out_of_window) if (i + 1) % n == 0]
    if kind == "per_shot_cycle_from_own_burst_to_full_burst_end":
        # ("per_shot_cycle_from_own_burst_to_full_burst_end", first, period):
        # fires at the `first`-th shot of the status window and every `period`
        # after, with the count RESTARTED IN EACH WINDOW. That restart is the
        # whole difference from "per_shot_every_during_own_status_window", which
        # concatenates every window's shots before counting - fine for a status
        # whose own stacks reset anyway, wrong for a phase rotation, where a
        # window holding a non-multiple of `period` shots would drag the phase
        # into the next window and never line up again.
        #
        # The window is the span of a status the owner's OWN burst grants and
        # the end of Full Burst removes: it opens at each of her burst times and
        # closes at the first Full Burst end after it. Its length is a property
        # of the DECK, not a constant - the Burst 3 that opened that cycle may
        # have moved the window (Isabel -5 sec, Modernia +5 sec), and her burst
        # is a tier gap earlier than the window's own start. Reading the end off
        # `full_burst_windows` is what keeps this fill and the buff half of the
        # same status (open-ended + `truncate_open_ended` at `full_burst_end`)
        # describing one window instead of two that disagree. A burst with no
        # Full Burst left to close it runs to the end of the fight.
        #
        # Arcana: Fortune Mate's Memories and Moments is the shape this exists
        # for: while Making Memories is up, every 2nd normal attack triggers ONE
        # of three effects in rotation (2 reload, 4 Happy Memories, 6 Precious
        # Moments, then 8/10/12, ...), and the count resets when the status is
        # removed. Each effect is one (first, period) pair on the same rotation.
        first, period = fill[1], fill[2]
        times = []
        for burst_time in own_burst_times:
            end = next((e for _start, e in full_burst_windows if e > burst_time), fight_duration)
            in_window = [t for t in shot_times if burst_time <= t < end]
            times.extend(t for i, t in enumerate(in_window)
                         if i + 1 >= first and (i + 1 - first) % period == 0)
        return sorted(times)
    if kind == "per_shot_every_outside_full_burst":
        n = fill[1]
        # Closed on the right: a shot landing exactly at a Full Burst window's
        # end still belongs to the burst moment, not "outside" it. Left open
        # (< end) would make outside-FB firing depend on which side of the
        # float boundary a coincident shot rounds to (e.g. a transform tick
        # nominally at burst+duration == FB end).
        out_of_window = [
            t for t in shot_times if not any(start <= t <= end for start, end in full_burst_windows)
        ]
        return [t for i, t in enumerate(out_of_window) if (i + 1) % n == 0]
    if kind == "on_last_bullet":
        return sorted(last_bullet_times)
    if kind == "at_battle_start":
        return [0.0]
    if kind == "on_full_burst_end_after_own_burst":
        # Mihara's Restraint Chains: re-banked when Full Burst ends "if this
        # unit has just used her Burst Skill", and spent whole just AFTER that
        # ("풀 버스트 타임 종료 후"). The later Burst-Stage-3 discharge trigger
        # then always finds an empty bank, so this is the only recurring
        # discharge in a raid. The nudge past the window's end is what the
        # skill text says AND what makes the discharge survive a resource
        # reset landing on that same instant (Bonding Pain cancelling the
        # stacks it just detonated) - resource_count discards fills recorded
        # at or before its baseline reset.
        times = []
        for burst_time in own_burst_times:
            end = next((e for s, e in full_burst_windows if s <= burst_time <= e), None)
            if end is not None and end + AFTER_WINDOW_EPSILON not in times:
                times.append(end + AFTER_WINDOW_EPSILON)
        return sorted(times)
    raise ValueError(f"unknown resource fill kind: {kind}")


def _fill_sources(fill):
    """A resource's `fill` is either ONE fill spec (granting 1 stack a time,
    the shape every pre-existing consumer uses) or a list of (fill spec,
    amount) pairs for a resource fed by several sources at different rates -
    e.g. Mihara's Ensnaring Chains, +10 per chain discharge and +1 per 40
    normal attacks during Full Burst."""
    if isinstance(fill, list):
        return fill
    return [(fill, 1)]


def _round_grant_over_cap(index, grant, start, end, windows):
    """Whether this "for N round(s)" grant exceeds its skill's "stacks up to N
    time(s)" cap on THIS recipient, and so must not be applied. `windows` holds
    every grant hitting this one recipient with the shot window it resolved to,
    in the order they were granted; a grant is over cap when `cap` OR MORE
    grants of the same cap group overlap it and were granted later. That keeps
    the most recent `cap` stacks of any mutually-overlapping set, matching how
    the game pushes the oldest stack out when a new one lands on a full stack.
    Uncapped grants (cap None - every consumer that predates the cap) never
    match and are emitted exactly as before."""
    if grant.cap is None:
        return False
    newer_overlapping = sum(
        1
        for other_index, (other, other_start, other_end) in enumerate(windows)
        if other.cap_group == grant.cap_group
        # Grants can share a granted_at (one trigger, several recipients'
        # timelines aside, or two rules firing together), so the tie is broken
        # by grant order - exactly one of any pair counts as newer.
        and (other.granted_at, other_index) > (grant.granted_at, index)
        and other_start < end
        and start < other_end
    )
    return newer_overlapping >= grant.cap


def _sequence_fire_rules(spec, stage_rules, shot_times, own_burst_times):
    """gap #10 (Scarlet's Fleetly Fading Breakthrough): one running shot
    counter walks a staged requirement table - stage k fires its rules once
    the count reaches spec["requirements"][k], and after the last stage the
    count resets and the cycle restarts. Inside the owner's own-burst window
    (spec["own_burst_window"] = (duration, alt_requirements), e.g. Scarlet's
    burst "Changes Full Charge attack count required for Skill 1 to 1/2/3 for
    10 sec") the requirement table is swapped in place; the running count and
    stage CARRY OVER across the boundary (Fienn 2026-07-18) - a stage fires
    once count >= the ACTIVE requirement for it, so progress made under one
    table is never lost under the other. At most one stage fires per shot
    ("Only one effect is triggered at a time"). Returns {shot_time: rules}."""
    base_reqs = spec["requirements"]
    override = spec.get("own_burst_window")
    windows = ()
    override_reqs = base_reqs
    if override:
        duration, override_reqs = override
        windows = [(bt, bt + duration) for bt in own_burst_times]
    fires = {}
    count, stage = 0, 0
    for t in shot_times:
        count += 1
        reqs = override_reqs if any(start <= t < end for start, end in windows) else base_reqs
        if count >= reqs[stage]:
            fires[t] = stage_rules[stage]
            stage += 1
            if stage == len(base_reqs):
                count, stage = 0, 0
    return fires


def _resolve_squad_burst_cycle_resource(spec, slug, events, context):
    """Fills/resets a resource driven by GLOBAL burst-cycle events (not the
    owner's own shots), where the fill is CONDITIONAL on the resource's own
    running value - e.g. Maiden's MP: "+1 if MP==0" whenever ANY squad
    tier-1 fires, "+1 if MP>=1" on entering Full Burst. This can't be a flat
    deterministic schedule (see `_resource_fill_times`) because whether a
    fill applies depends on state that changes as events are processed, so
    it's walked as a genuine sequential replay instead.

    fill = ("squad_burst_cycle_conditional", rules), rules a list of
    (event_matcher, condition_fn, delta): event_matcher(event) -> bool tests
    one of simulate_burst_cycle's own events (e.g. {"type": "burst", "tier":
    1, ...} or {"type": "full_burst_start", ...}); condition_fn(count) -> bool
    gates the fill on the CURRENT running value.

    Only `spec.resets` with trigger "own_burst" is supported (checked inline
    against each event's own slug, at the exact point it occurs in `events` -
    not merged in afterward) - "battle_start" is applied once before the
    walk begins. This preserves exact same-instant ordering from `events`
    (e.g. the owner's own burst always precedes full_burst_start, per the
    strict burst1->burst2->burst3->full-burst rule), which a resource whose
    fill depends on that exact ordering needs. `spec.buffs` isn't supported
    for this fill kind (no current consumer needs a continuous buff off a
    squad-burst-cycle-driven resource)."""
    rules = spec.fill[1]
    running = 0.0
    for reset_spec in spec.resets:
        if reset_spec["trigger"] == "battle_start":
            context.reset_resource(slug, spec.name, 0.0, running, reset_spec["value"])
            running = min(spec.cap, reset_spec["value"])
    own_burst_reset_value = next(
        (r["value"] for r in spec.resets if r["trigger"] == "own_burst"), None
    )
    for event in events:
        for matcher, condition, delta in rules:
            if matcher(event) and condition(running):
                running = min(spec.cap, running + delta)
                context.fill_resource(slug, spec.name, delta, event["time"])
        if own_burst_reset_value is not None and event.get("type") == "burst" and event.get("slug") == slug:
            pre_value = running
            running = own_burst_reset_value
            context.reset_resource(slug, spec.name, event["time"], pre_value, running)


# Each damage instance has a damage_type. The type-specific Damage-Up buckets
# below are read from the registry ONLY for instances of that type, so a buff
# like "Sustained Damage +X%" only boosts sustained-typed damage (not every
# hit). The always-on buckets (attack_damage_up, pierce/parts/damage_taken) are
# applied to every instance regardless of type - see _damage_instance. "attack"
# is the default type and adds no type-specific bucket, so untyped instances
# are computed exactly as before.
_TYPE_BUCKETS = {
    "attack": [],
    # Core strike carries no Damage-Up bucket of its own; what makes it
    # different is the core bonus it collects - see core_eligible.
    "core_strike": [],
    "sustained": ["sustained_damage_up"],
    "distributed": ["distributed_damage_up"],
    "true": ["true_damage_up"],
    "projectile_explosion": ["projectile_explosion_damage_up"],
    "projectile_attachment": ["projectile_attachment_damage_up"],
    # A multi-hit "attacks sequentially" volley (Snow White: Heavy Arms' Auto
    # Fire). Only the sequential hits carry it - the same skill's all-enemy
    # sweep rides the plain "attack" type.
    "sequential": ["sequential_attack_damage_up"],
}

# Every registry stat phase-2 damage computation can read (_damage_instance,
# _normal_attack_percent). All are constant within one state epoch, so the
# whole bundle is resolved once per (target, epoch, registry version) - see
# _stat_bundle in _simulate_raid_once. normal_attack_type reads its single stat
# directly - it runs in phase 1 where per-shot mutations churn the version,
# so bundle misses there cost more than they save.
_BUNDLE_STATS = (
    "enemy_def_percent", "atk_percent", "flat_atk", "other_elemental_bonus",
    "element_advantage_grant",
    "other_critical_damage_sources", "crit_rate", "other_core_damage_sources",
    "charge_damage_bonus", "attack_damage_up", "damage_to_parts_up",
    "pierce_damage_up", "has_pierce", "damage_taken_up",
    "sustained_damage_up", "distributed_damage_up", "true_damage_up",
    "projectile_explosion_damage_up", "projectile_attachment_damage_up",
    "sequential_attack_damage_up",
    "normal_attack_damage_multiplier",
    "normal_attack_crit_rate",
    "hit_rate",
)


# 조건부 풀 버스트 확장(소다의 Beginner's Rewards)이 있는 덱에서 고정점을 찾는
# 패스 수의 상한. 하한(확장 없음)에서 출발해 위로 가므로 수렴은 단조롭게 오르는
# 방향이고, 이 상한은 수렴하지 않는 조합에서 무한히 도는 것을 막는 안전장치다.
#
# 필요한 패스 수는 덱 구성이 아니라 **전투 길이**의 함수다: 확장이 사이클 k의
# 창을 늘리면 그 창의 사격이 사이클 k+1의 칩을 바꾸므로, 변화는 패스마다 한
# 사이클씩 앞으로 번진다. 격 사이클 덱을 길이별로 쓸면 3패스(200초) / 5(400초) /
# 7(600초) / 8(700초 이후 평평)이고, 7200초 - 게임 최대의 40배 - 까지 재도 8이다
# (2026-08-08). 그러므로 32는 이 확장에 대해 4배 마진이고, 여기 걸리려면 진동해서
# 수렴하지 않는 조합이어야 한다. 걸리면 조용하지 않다:
# `FullBurstConvergenceWarning`을 낸다.
#
# 그래서 「관측된 최악의 두 배」식 마진은 전투 길이가 고정일 때만 마진이다.
# `fight_duration`은 사용자 입력이고(`BossProfileField.tsx`의 폼 필드, api.py의
# 180.0은 기본값일 뿐) 700초를 넣으면 상한 8에 정확히 닿는다 - 여유 0이다.
# 상한에 걸린 답은 고정점이 아닌 채 `converged: False`만 달고 조용히 나가는데,
# 그 플래그를 읽는 하류가 없어 오답이 damage 숫자로 나간다.
#
# 32는 품질 노브가 아니라 폭주 방지 장치의 값이다. 수렴하는 덱은 상한과 무관하게
# 실제 패스 수만 지불하므로(700초 덱은 32에서도 여전히 8패스에서 끝난다) 값을
# 키우는 비용은 **진동해서 영영 안 끝나는 병리적 조합에만** 붙고, 그런 조합은
# 어차피 답이 없다.
MAX_FULL_BURST_PASSES = 32


class FullBurstConvergenceWarning(UserWarning):
    """고정점 루프가 상한을 다 쓰고도 자기 입력을 재생산하지 못했다.

    이 경고가 붙은 결과의 `total_damage`는 고정점이 아니다 - 마지막 패스가 낸
    답일 뿐이라 창 길이가 실제와 다르고, 다른 덱과 비교할 수 있는 숫자가 아니다.

    전용 클래스인 이유는 둘이다: `pytest.warns`가 다른 경고와 헷갈리지 않고
    이것만 겨눌 수 있고, 언젠가 이것만 골라 끄고 싶어질 때 축이 있다.
    `UserWarning` 하위라 파이썬 기본 필터에서 안 무시된다.
    """


# 자원 조회를 리셋 "직전"으로 밀어내는 폭. resource_count는 조회 시각과 같은
# 시각의 리셋을 베이스라인으로 쓰므로, 그냥 버스트 시각을 물으면 소비 후 값이
# 돌아온다. 이 폭이면 같은 순간의 리셋만 벗어나고 직전 fill은 그대로 센다.
#
# `FULL_BURST_OPEN_DELAY`와 값이 같은 것은 우연이다 - 저쪽은 버스트 발동과 창
# 개시를 가르는 폭이고 이쪽은 자원 조회를 리셋 앞으로 미는 폭이라, 한쪽이 바뀌어도
# 다른 쪽을 따라 바꿀 이유가 없다.
_PRE_BURST_EPSILON = 1e-6


def _resolve_conditional_fb_deltas(context, events, conditional_full_burst_deltas):
    """사이클별 {슬러그: 확장 단계}. 단계는 그 사이클의 Burst 3이 발동한 순간,
    자원이 소비되기 직전의 값으로 정해진다.

    원문이 "Activates when entering Burst Stage 3 / Affects all allies"이므로
    스펙 보유자가 그 사이클의 Burst 3일 필요가 없다 - 덱에 있고 조건이 맞으면
    누가 창을 열든 걸린다. 판정 시각도 `full_burst_start`가 아니라 버스트
    발동 시각이다(둘은 FULL_BURST_OPEN_DELAY만큼 떨어져 있다).

    단계 0은 담지 않는다: 아무 유닛도 조건을 못 넘긴 사이클은 키 자체가 없어야
    "빈 딕셔너리"와의 비교로 고정점을 판정할 수 있다."""
    resolved = {}
    if not conditional_full_burst_deltas:
        return resolved
    tier3_times = [e["time"] for e in events if e.get("type") == "burst" and e.get("tier") == 3]
    for cycle_index, fire_time in enumerate(tier3_times):
        stages = {}
        for slug, spec in conditional_full_burst_deltas.items():
            count = context.resource_count(
                slug, spec["resource"], fire_time - _PRE_BURST_EPSILON, spec["cap"]
            )
            # 임계는 "이상"이다: 소다의 소비 시퀀스는 정확히 20에 내려앉는데 그게
            # II단계의 임계라, 여기서 한 칸 어긋나면 실제 딜이 바뀐다.
            #
            # 마지막으로 통과한 tier가 답인 것은 tiers가 임계 오름차순이기 때문이다
            # (`build_beginners_rewards_full_burst_delta`가 그렇게 만든다).
            # `_stage_seconds`의 `tiers[stage - 1]`도 같은 순서를 전제하므로, 순서가
            # 깨지면 두 곳이 함께 틀린다.
            stage = 0
            for index, (threshold, _seconds) in enumerate(spec["tiers"], start=1):
                if count >= threshold:
                    stage = index
            if stage:
                stages[slug] = stage
        if stages:
            resolved[cycle_index] = stages
    return resolved


def simulate_raid(*args, **kwargs):
    """한 번의 레이드 시뮬레이션. 대부분의 덱에서는 `_simulate_raid_once`를 정확히
    한 번 부르는 것과 같다.

    풀 버스트 창 길이가 자원 상태에 달린 유닛(소다: 트윙클링 바니)이 덱에 있으면
    고정점까지 반복한다: 창 길이가 그 사이클 진입 시점의 골든칩으로 정해지는데,
    칩은 창 안의 사격으로 차고, 사격은 창이 정해져야 존재한다. 시간 순서로는
    인과가 한 방향이지만(사이클 k의 판정은 k-1까지의 샷만 본다) 이 엔진은
    스케줄러를 통째로 먼저 돌리므로 패스 단위로 같은 답에 도달한다.

    그런 유닛이 없으면 해석기가 빈 딕셔너리를 돌려주고 첫 패스에서 종료한다 -
    결과도 비용도 오늘과 같다.
    """
    overrides = {}
    result = None
    for attempt in range(MAX_FULL_BURST_PASSES):
        result, resolved = _simulate_raid_once(
            *args, **kwargs, full_burst_stage_overrides=overrides
        )
        if resolved == overrides:
            result["full_burst_passes"] = {"passes": attempt + 1, "converged": True}
            return result
        overrides = resolved
    result["full_burst_passes"] = {"passes": MAX_FULL_BURST_PASSES, "converged": False}
    # `converged: False`만으로는 아무도 못 본다 - 이 플래그를 읽는 하류가 없다.
    # 질의 헬퍼를 하나 더 만들어도 `scripts/`의 소비자 16개 중 2개만 부르는
    # `deck_search.never_full_bursts`의 전철을 밟는다. 경고는 소비자가 아무것도
    # 안 해도 닿고, `backend/pytest.ini`의 `filterwarnings = error` 아래에서는
    # 테스트 실패가 된다.
    #
    # 덱을 메시지에 안 싣는 것은 의도다: 파이썬 기본 필터가 (텍스트, 카테고리,
    # 위치)로 중복을 접으므로 덱마다 다른 텍스트를 내면 스윕 한 번이 수만 줄이
    # 된다. `fight_duration`은 요청당 사실상 하나라 접힌 채로도 재현에 쓸 수
    # 있고, 애초에 패스 수를 정하는 축이다.
    bound = inspect.signature(_simulate_raid_once).bind_partial(*args, **kwargs)
    warnings.warn(
        f"풀 버스트 확장이 {MAX_FULL_BURST_PASSES} 패스 안에 수렴하지 않았다 "
        f"(fight_duration={bound.arguments.get('fight_duration', '?')}) - "
        f"이 결과의 total_damage는 고정점이 아니다.",
        FullBurstConvergenceWarning,
        stacklevel=2,
    )
    return result


def _stage_seconds(stage_table, conditional_full_burst_deltas):
    """{사이클: {슬러그: 단계}}를 burst_cycle이 쓰는 {사이클: 초}로 바꾼다.

    단계는 유닛별이고 초는 창 하나에 하나뿐이라 합산한다 - 확장을 주는 유닛이
    둘 있는 덱이라면 창이 둘 다 만큼 길어진다. 오늘 소비자는 소다 하나뿐이라
    합이 곧 그녀 몫이다.

    단계는 1부터 센다. 0은 `SquadContext.full_burst_extension_stage`가 "확장
    없음"으로 돌려주는 값이라 이 표에 실릴 값이 아니고, `tiers[stage - 1]`에
    그대로 넣으면 `tiers[-1]`로 감겨 최대 단계를 조용히 사게 된다. 범위를 벗어난
    단계는 생산자가 계약을 어겼다는 뜻이므로 건너뛰지 말고 터뜨린다 - 삼키면
    버그가 예외가 아니라 damage 숫자로 나온다."""
    seconds = {}
    for cycle_index, stages in stage_table.items():
        total = 0.0
        for slug, stage in stages.items():
            tiers = conditional_full_burst_deltas[slug]["tiers"]
            if not 1 <= stage <= len(tiers):
                raise ValueError(
                    f"full burst extension stage {stage} for {slug!r} in cycle "
                    f"{cycle_index} is outside 1..{len(tiers)} - stage 0 means "
                    f"'no extension' and belongs out of this table, not in it")
            total += tiers[stage - 1][1]
        if total:
            seconds[cycle_index] = total
    return seconds


def _simulate_raid_once(
    deck,
    rules_by_slug,
    burst_damage_percents,
    base_stats,
    enemy_def,
    gauge_charge_time,
    fight_duration,
    mode="auto",
    core_hittable=False,
    weapon_stats=None,
    boss_element=None,
    part_destructible=False,
    # A boss that keeps its core as a separate object from its body: a Pierce
    # holder's shot passes through the core and lands on the body behind it, so
    # one normal attack produces two instances (Fienn, 2026-08-03). Read together
    # with `core_hittable` below - there is no 2-pierce without a core to pierce,
    # so a caller that sets this without core_hittable gets nothing.
    pierce_hits_body_behind_core=False,
    core_diameter_px=None,
    effective_range_band=None,
    base_crit_rate=BASE_CRIT_RATE,
    periodic_nukes=None,
    burst_damage_types=None,
    burst_resolves_after_cast=None,
    periodic_rules=None,
    per_shot_rules=None,
    resource_specs=None,
    burst_hit_counts=None,
    resource_scaled_nukes=None,
    resource_gated_buffs=None,
    dynamic_hit_count_nukes=None,
    resource_fill_triggered_buffs=None,
    scheduled_nukes=None,
    weapon_mode_schedules=None,
    burst_anchored_buffs=None,
    ammo_rounds_per_shot=None,
    conditional_full_burst_deltas=None,
    full_burst_stage_overrides=None,
    collect_target_grants=False,
    # {slug: [양 옆 아군 둘]} - "자신과 양 옆 아군 2명" 불릿의 좌석. 안 주면
    # SquadContext.neighbor_slugs의 정책이 답한다.
    adjacency=None,
):
    weapon_stats = weapon_stats or {}
    # None means "no band read for this encounter", which pays nobody. An
    # unrecognised band raises rather than quietly paying nobody, since the two
    # are indistinguishable in the output.
    if effective_range_band is not None and effective_range_band not in EFFECTIVE_RANGE_BANDS:
        raise ValueError(
            f"unknown effective range band {effective_range_band!r} - "
            f"expected one of {sorted(EFFECTIVE_RANGE_BANDS)} or None")
    in_range_weapons = EFFECTIVE_RANGE_BANDS.get(effective_range_band, frozenset())
    weapon_mode_schedules = weapon_mode_schedules or {}
    periodic_nukes = periodic_nukes or {}
    burst_damage_types = burst_damage_types or {}
    burst_resolves_after_cast = burst_resolves_after_cast or set()
    periodic_rules = periodic_rules or {}
    per_shot_rules = per_shot_rules or {}
    resource_specs = resource_specs or {}
    burst_hit_counts = burst_hit_counts or {}
    resource_scaled_nukes = resource_scaled_nukes or {}
    resource_gated_buffs = resource_gated_buffs or {}
    dynamic_hit_count_nukes = dynamic_hit_count_nukes or {}
    resource_fill_triggered_buffs = resource_fill_triggered_buffs or {}
    scheduled_nukes = scheduled_nukes or {}
    ammo_rounds_per_shot = ammo_rounds_per_shot or {}
    conditional_full_burst_deltas = conditional_full_burst_deltas or {}
    full_burst_stage_overrides = full_burst_stage_overrides or {}
    # 대상 판정 기록은 계산기 화면 전용이라 기본이 off다. 켜져야만 리스트가
    # 생기고, 그래야 탐색이 도는 수만 번의 시뮬이 오늘과 같은 할당을 한다.
    target_grants = [] if collect_target_grants else None
    context = SquadContext(
        [SquadMember(m["slug"], m["burst_tier"], m["element"], m.get("weapon")) for m in deck],
        base_atk={m["slug"]: base_stats[m["slug"]]["atk"] for m in deck},
        base_charge_time={
            m["slug"]: (weapon_stats.get(m["slug"]) or {}).get("charge_time", 0.0)
            for m in deck
        },
        boss_element=boss_element,
        part_destructible=part_destructible,
        core_hittable=core_hittable,
        target_grants=target_grants,
        adjacency=adjacency,
    )
    registry = EffectRegistry()
    # Damage is RECORDED as events during phase 1 (buffs are applied but no
    # damage is computed yet), then computed in a single phase-2 pass once EVERY
    # buff/debuff is in the registry - so e.g. a per-shot squad debuff applied
    # mid-fight correctly raises a burst nuke that fired earlier. Effects are
    # replay-safe (added with applied_at >= their time; truncate_open_ended
    # mutates in place), so deferring computation never changes an existing
    # value - only lets late buffs reach instances they should have.
    damage_events = []
    member_by_slug = {m["slug"]: m for m in deck}

    def target_for(slug):
        return {"slug": slug, "element": member_by_slug[slug]["element"]}

    stat_bundles = {}

    def _stat_bundle(slug, time):
        # All _BUNDLE_STATS are constant within one state epoch, so resolve
        # them once per (target, epoch); the version key drops stale bundles
        # whenever the registry mutates, which keeps replay-late effects
        # behaving exactly as per-stat queries did.
        # Phase-2 only: do NOT call this from phase 1 - per-shot mutations
        # churn the version there, so every call misses, rebuilds the whole
        # bundle, and grows the memo (see the _BUNDLE_STATS note).
        target = target_for(slug)
        key = (slug, registry.state_epoch(target, time), registry.version)
        bundle = stat_bundles.get(key)
        if bundle is None:
            bundle = {stat: registry.total_for(stat, target, time) for stat in _BUNDLE_STATS}
            stat_bundles[key] = bundle
        return bundle

    def element_bonus_for(slug, advantage_grant=0.0):
        """The unit's Element Bonus multiplier: 1.1 when it holds elemental
        advantage over the boss, else 1.0.

        `advantage_grant` (> 0) is a skill that GRANTS advantage the unit does
        not naturally have - "applies Elemental Advantage damage to <Code>
        enemies" (Rapi: Red Hood). It is deliberately NOT the same stat as
        other_elemental_bonus ("Superior Code Damage"), which only pays out to
        a unit that ALREADY has advantage: a granted advantage is real
        advantage, so it both raises this multiplier and opens damage_formula's
        advantage gate for any Superior Code bonus the unit carries."""
        if boss_element is None:
            return 1.0
        if advantage_grant > 0:
            return 1 + ELEMENT_ADVANTAGE_BONUS
        return element_multiplier(member_by_slug[slug]["element"], boss_element)

    def _in_effective_range(slug, is_normal_attack, damage_type):
        """Whether this instance collects the Effective Range bonus.

        The encounter decides the distance (`BossProfile.effective_range_band`)
        and that band decides WHICH weapons are in range - a mid-range boss
        pays an AR and an MG, not an SG. Neither the engine nor the player
        picks it, so unlike the core-hit assumption this is never taken for
        granted. What the engine does decide is the SCOPE, which is Core
        Damage's scope exactly: normal attacks only, and never
        Sustained/Distributed even when those are the unit's normal attack.
        """
        if not (is_normal_attack and damage_type not in NON_CORE_DAMAGE_TYPES):
            return False
        # Read off weapon_stats, which describes the weapon that fired the
        # shot, rather than the deck entry - `weapon` is optional there
        # (`SquadMember` takes it with .get). A slug absent from weapon_stats
        # fires no normal attacks, so it never reaches this line.
        #
        # A weapon-mode segment does NOT change the band, even when its profile
        # names a different weapon class: Nayuta transforms SMG -> an "SR"
        # profile, and her transformed shots keep SMG's near band (Fienn,
        # 2026-08-03, residual 5.8e-08 against 8.20% for profile banding -
        # docs/measurements/weapon-transform-effective-range-band.md). Reading
        # the unit's weapon_stats is therefore correct for segment shots too.
        weapon = (weapon_stats.get(slug) or {}).get("weapon")
        return weapon in in_range_weapons

    def _core_hit_rate_at(slug, time, is_normal_attack, always_core_hit=False,
                          magazine_index=None, declared_spread=None):
        """이 인스턴스의 발 중 코어에 드는 비율.

        `magazine_index`는 이 발이 탄창의 몇 번째인가다 — MG의 조준원은 탄창이
        비어 갈수록 조여지므로 같은 유닛의 같은 명중률에서도 발마다 값이 다르다
        (`accuracy.SPREAD_CONVERGENCE`). 탄창 위치가 없는 인스턴스는 수렴값을
        받는다.

        탄착군이 좌우하는 것은 평타뿐이다. `core_strike`는 스킬이 코어를
        때린다고 원문에 적힌 딜이고, 소환물은 스스로 조준하므로(아니스:
        스타의 Shooting Stars) 둘 다 겨냥의 문제가 아니다 - 둘 다 평타가
        아니라서 이 한 줄로 함께 걸러진다.

        `core_diameter_px`가 없으면 이 인카운터는 코어히트율을 모델링하지
        않는다: 적격 인스턴스는 엔진이 오래 모델해 온 상한인 1.0을 받는다.

        무기변형 세그먼트의 발도 탄착군은 기저 무기(`weapon_stats`)로 찾는다 -
        세그먼트가 다른 무기 클래스를 자칭해도(나유타 SMG -> "SR" 프로필) 그
        라벨은 안 쓴다. `_in_effective_range`의 같은 선택은 실측이
        뒷받침한다(잔차 5.8e-08,
        docs/measurements/weapon-transform-effective-range-band.md). 여기는
        아니다 - 세그먼트의 `"weapon"`은 스킬 모듈에 손으로 적힌 무기 클래스
        라벨일 뿐, `shot_detail`이 잰 그 세그먼트의 실제 조준원이 아니다.
        `WEAPON_SPREAD_DIAMETER`를 그 라벨로 찾으면 없는 탄착군 수치를 지어내는
        셈이 된다.

        그래서 세그먼트가 조준원을 바꾸는 경우는 라벨이 아니라 **선언**으로
        들어온다. 선언은 둘이고 둘 다 실측에서만 온다:

        - `always_core_hit` — 그 세그먼트는 코어를 언제나 맞힌다(p=1.0).
          나유타 · 츠바이 · 스노우화이트가 그렇다(Fienn 인게임 확인).
        - `spread_diameter` — 코어 고정은 아니지만 조준원을 **재서** 아는 경우.
          모란의 창모드가 그렇다(기저 AR 75에 대해 150).

        선언이 없는 세그먼트는 여전히 기저 무기를 쓰고, 그 근사는 미측정으로
        남는다. 다만 기저가 SR/RL이거나 수렴한 MG면 지름 10이 코어보다 좁아
        어차피 1.0이므로, 근사가 실제로 무는 건 기저가 AR/SMG/SG인 세그먼트뿐이다
        (docs/engine-gaps.md의 재집계).
        """
        if core_diameter_px is None or not is_normal_attack or always_core_hit:
            return 1.0
        if declared_spread is not None:
            return core_hit_rate(None, _stat_bundle(slug, time)["hit_rate"],
                                 core_diameter_px, base_diameter=declared_spread)
        weapon = (weapon_stats.get(slug) or {}).get("weapon")
        if weapon not in WEAPON_SPREAD_DIAMETER:
            # accuracy.spread_diameter는 모르는 무기에 KeyError를 던진다(근거
            # 없는 탄착군을 지어내지 않으려고). 여기서 대신 1.0을 주는 것은 그
            # 규칙을 깨는 게 아니라, 이 opt-in 경로 전체가 이미 1.0을 중립값으로
            # 쓰기 때문이다(core_diameter_px가 None일 때와 같은 값) - 모르는
            # 무기는 지어낸 탄착군 대신 예전의 상한 동작으로 떨어진다.
            return 1.0
        return core_hit_rate(
            weapon, _stat_bundle(slug, time)["hit_rate"], core_diameter_px,
            magazine_index
        )

    def _damage_instance(
        slug, percent, time, damage_type="attack", extra_charge_bonus=0.0, extra_flat_atk=0.0,
        hits_core=False, on_charge_weapon=None, is_normal_attack=False, core_hit_share=1.0,
    ):
        bundle = _stat_bundle(slug, time)
        # True Damage ignores enemy DEF (nikke.gg glossary).
        instance_enemy_def = 0 if damage_type == "true" else enemy_def
        # The Full Burst Bonus is decided by WHEN this instance's damage is
        # computed - if that moment falls inside a Full Burst window, it gets
        # the bonus (Fienn, 2026-07-28). There is nothing else to it, and in
        # particular no skill-text test: an earlier rule read "as additional
        # damage" out of the description, which only ever correlated because a
        # Burst 3's instant "as damage" bullets resolve at the cast, one beat
        # BEFORE the window opens. Now that cast time and Full Burst entry are
        # separate instants, the time answers it directly - so what a caller
        # must get right is the instance's TIME (see `resolves_after_cast`),
        # not some eligibility flag.
        in_full_burst = any(
            start <= time < end for start, end in full_burst_windows
        )
        terms = dict(
            atk=base_stats[slug]["atk"],
            attack_coefficient=percent / 100,
            enemy_def=instance_enemy_def,
            enemy_def_percent=bundle["enemy_def_percent"],
            atk_percent=bundle["atk_percent"],
            flat_atk=bundle["flat_atk"] + extra_flat_atk,
            other_elemental_bonus=bundle["other_elemental_bonus"],
            other_critical_damage_sources=bundle["other_critical_damage_sources"],
            # "Critical Rate of normal attack" is a second crit-rate bucket the
            # SKILL scopes to normal attacks (Helm's Frontline Command, Julia
            # signature's Decrescendo). Unlike Core Damage and Effective Range
            # crit is not a normal-attack-exclusive modifier in the formula, so
            # the only gate is the instance being a normal attack. The cap sits
            # on the SUM, which is why it is added before the min.
            crit_rate=min(1.0, base_crit_rate + bundle["crit_rate"] + (
                bundle["normal_attack_crit_rate"] if is_normal_attack else 0.0
            )),
            core_hit_rate=core_hit_share,
            core_hit_bonus=core_hit_bonus_for(slug) if hits_core else 0.0,
            other_core_damage_sources=(
                bundle["other_core_damage_sources"] if hits_core else 0.0
            ),
            full_burst_bonus=1.0 if in_full_burst else 0.0,
            # Effective Range is scoped exactly like Core Damage - normal
            # attacks only, and never Sustained/Distributed even when those ARE
            # the unit's normal attack - with one weapon carved out: a Rocket
            # Launcher collects it at no distance at all (Fienn, 2026-07-28;
            # engine-gaps item 16 for the measurement that fixed the +0.30).
            effective_range_bonus=(
                1.0 if _in_effective_range(slug, is_normal_attack, damage_type) else 0.0
            ),
            element_multiplier=element_bonus_for(slug, bundle["element_advantage_grant"]),
            # Charge Damage multiplies a fully-charged SHOT and nothing else.
            # It is one of the damage formula's asterisked terms - "Modifiers
            # with an asterisk (*) are exclusive to Normal Attacks only", and
            # its glossary entry reads "Damage bonus available to Charge
            # weapons' normal attacks ... Charge Damage Sources include buffs
            # from the unit or allies" (nikke.gg/damage-formula, the reference
            # this module implements; the project's own
            # references/damage-formula-reference.md says the same).
            #
            # So a skill that fires ON a Full Charge - Scarlet's staged nukes,
            # Velvet's Bullets of Love, Neon's Firepower Explosion - is a
            # separate damage instance and collects none of it, however
            # charged the shot that triggered it was.
            #
            # Only the normal-attack path passes on_charge_weapon, and it
            # answers per shot because a weapon transform can flip mid-fight
            # (Nayuta's burst turns her SMG into a charge attack for 10 sec).
            charge_damage_bonus=(
                bundle["charge_damage_bonus"] + extra_charge_bonus
                if on_charge_weapon
                else 0.0
            ),
            attack_damage_up=bundle["attack_damage_up"],
            damage_to_parts_up=bundle["damage_to_parts_up"],
            # Pierce Damage Up buffs PIERCE, and Pierce is a property of normal
            # attacks - "normal attacks hitting everything in their path"
            # (references/damage-formula-reference.md). So it needs BOTH that
            # the unit currently has Pierce and that this instance is her normal
            # attack: a skill nuke fired by a piercing unit is not pierce damage
            # and collects none of it. Gating on `has_pierce` alone leaked the
            # bucket into every instance the unit produced - caught on Snow
            # White: Heavy Arms, whose Auto Fire pulses were carrying her
            # +13.09% (Fienn, range footage 2026-07-28).
            pierce_damage_up=(
                bundle["pierce_damage_up"]
                if is_normal_attack and bundle["has_pierce"] > 0
                else 0.0
            ),
            damage_taken_up=bundle["damage_taken_up"],
        )
        # Type-specific Damage-Up buckets apply only to instances of that type.
        for bucket in _TYPE_BUCKETS[damage_type]:
            terms[bucket] = bundle[bucket]
        return calculate_damage(**terms)

    def normal_attack_type(slug, weapon_type, time):
        # A skill can convert a unit's normal attacks to a damage type for a
        # window (e.g. Takina Inoue's burst: "normal attacks deal true damage").
        if registry.total_for("normal_attacks_deal_true", target_for(slug), time) > 0:
            return "true"
        # Otherwise a rocket launcher's normal attacks are projectile explosions.
        if weapon_type == "RL":
            return "projectile_explosion"
        return "attack"

    def record(
        slug, percent, time, source, damage_type="attack",
        extra_charge_bonus=0.0, resource_gate=None, extra_flat_atk=0.0,
        on_charge_weapon=None, core_eligible_override=None, always_core_hit=False,
        spread_diameter=None,
        magazine_index=None,
    ):
        damage_events.append({
            "slug": slug, "percent": percent, "time": time, "source": source,
            "damage_type": damage_type, "extra_charge_bonus": extra_charge_bonus,
            "resource_gate": resource_gate, "extra_flat_atk": extra_flat_atk,
            # None = decide from the unit's base weapon; a normal attack pins
            # the weapon its own shot record actually fired.
            "on_charge_weapon": on_charge_weapon,
            # None = apply `core_eligible`'s general rule. True opts one
            # instance in against it - see that function's summon exception.
            "core_eligible_override": core_eligible_override,
            # This shot came from a weapon-mode segment that declares it always
            # lands on the core, so no spread math applies to it.
            "always_core_hit": always_core_hit,
            # A segment that MEASURED its own aiming circle rather than being
            # core-locked, in accuracy.WEAPON_SPREAD_DIAMETER's units. None =
            # fall back to the base weapon's.
            "spread_diameter": spread_diameter,
            # Which round of its magazine this was, for the weapons whose aiming
            # circle tightens as the magazine empties. None = not a magazine
            # round, so the converged diameter applies.
            "magazine_index": magazine_index,
        })

    def _resolve_percent(ev):
        # A resource-scaled/gated nuke's recorded percent is a BASE value; its
        # real magnitude depends on the resource's count at the event's OWN
        # time, which isn't known until the resolution pass runs (after the
        # burst cycle that records this event) - so it's resolved here, in
        # phase 2, exactly like a deferred buff (see module docstring).
        if ev["resource_gate"] is None:
            return ev["percent"]
        name, cap, lifetime, scale_fn = ev["resource_gate"]
        count = context.resource_count(ev["slug"], name, ev["time"], cap, lifetime)
        return ev["percent"] * scale_fn(count)

    def drain_instant_damage(time):
        # A passive that deals damage on a trigger OTHER than the caster's own
        # burst (e.g. Brid: Silent Track's Ignition Sequence, on full_burst_enter)
        # can't use burst_damage_percents (tied to own_burst_activate). It emits
        # an "instant_damage_percent" pulse instead; drained here after every
        # trigger fire, recorded as a nuke computed later like a burst nuke.
        for pulse in registry.drain_pulses("instant_damage_percent"):
            record(
                pulse.source_slug, pulse.value, time, "instant_nuke",
                damage_type=pulse.damage_type,
            )

    def on_battle_start(time):
        fire_trigger("battle_start", rules_by_slug, context, registry, time)
        drain_instant_damage(0.0)
        # A burst-cooldown cut emitted at battle start has nothing to cut: no
        # burst has been used, so every unit's last-used time is -inf and the
        # reduction is a no-op. Draining it here is what makes it one - pulses
        # are otherwise collected only at Full Burst end, so this one would be
        # banked and paid against the FIRST cycle's real cooldowns on top of
        # that cycle's own cut (Anis: Star grants hers on both battle_start and
        # full_burst_end; in game the squad receives 7.48 sec after cycle one,
        # not twice that - Fienn, 2026-08-05).
        registry.drain_pulses("burst_cooldown_reduction_sec")

    def on_tier_fire(tier, slug, time):
        context.burst_used_this_cycle.add(slug)
        context.last_burst_slug = slug
        context.record_burst_time(slug, time)
        fire_trigger("own_burst_activate", {slug: rules_by_slug.get(slug, [])}, context, registry, time)
        # Let other units react to THIS unit's burst (e.g. Prika's Encore firing
        # on Mint's Sing Along). Fired across every unit's rules AFTER the
        # burster's own own_burst_activate, so a reacting rule sees the burst's
        # own effects already applied.
        fire_trigger("ally_burst_activate", rules_by_slug, context, registry, time)
        # Drained after BOTH, so a reacting rule may deal damage and not only
        # apply buffs - Queen (Makoto Nijima) answers Yukiko's burst with a
        # distributed-damage nuke. Draining between the two left such a pulse
        # banked until the next drain point (Full Burst enter), which both
        # moved the hit off the burst it answered and paid it that window's
        # bonus. The burster's own pulses still drain at this same `time`, and
        # damage is computed in phase 2 against the final registry either way,
        # so no existing unit's output moves.
        drain_instant_damage(time)

        # A burst-fired nuke whose magnitude depends on a named resource's
        # count - a single gated/scaled additional hit (tick_count=1), or a
        # repeating tick (e.g. a Hero-Level-scaled DoT) where each tick reads
        # the count at ITS OWN time, not frozen at burst-fire time. Independent
        # of the plain burst_damage_percents nuke below (a unit can have
        # either, both, or neither).
        for spec in resource_scaled_nukes.get(slug, []):
            # An Ark Ranger Black-style spec may be bracketed to only one side
            # of the boss's part_destructible flag (e.g. a burst-anchored
            # floor DoT vs. a whole-fight ceiling DoT modeling the same
            # transformation state differently); absent field = always fires.
            required = spec.get("requires_part_destructible")
            if required is not None and required != context.part_destructible:
                continue
            # "resource" is optional: a plain repeating DoT with no resource
            # scaling (e.g. Mana's Fatal Error!) reuses this same tick_count/
            # tick_interval loop, just with no resource_gate to resolve later.
            resource_gate = (
                (spec["resource"], spec["cap"], spec.get("lifetime"), spec["scale_fn"])
                if spec.get("resource") is not None else None
            )
            # Same rule as the burst bullet below: a spec that opts into the
            # Full Burst bonus is one that resolves AFTER the cast, so its
            # ticks are anchored a beat later - which for a Burst 3 is the
            # instant Full Burst opens, putting even the first tick inside the
            # window (Mana's Fatal Error!, confirmed in-game).
            after_cast = spec.get("resolves_after_cast", False)
            tick_base = time + FULL_BURST_OPEN_DELAY if after_cast else time
            for i in range(spec["tick_count"]):
                tick_time = tick_base + i * spec["tick_interval"]
                record(
                    slug, spec["base_percent"], tick_time, "resource_scaled_nuke",
                    damage_type=spec.get("damage_type", "attack"),
                    resource_gate=resource_gate,
                )

        percent = burst_damage_percents.get(slug)
        if not percent:
            return
        # A burst that "attacks sequentially N times" deals N SEPARATE hits, not
        # one hit at N*percent - defense is a flat per-hit subtraction (see
        # damage_formula), so splitting into hits changes the total whenever
        # enemy_def > 0. All N hits land at the same instant.
        # `burst_resolves_after_cast` names the one thing a caller has to get
        # right: whether this burst's damage lands AT the cast or a beat later.
        # For a Burst 3 that beat is exactly when Full Burst opens, so a bullet
        # marked here is recorded inside the window (and sees any
        # full_burst_enter buff); an ordinary burst bullet stays at cast time,
        # before the window exists, and collects nothing. Which of the two a
        # unit gets is a reading of its skill, not of any one phrase in it.
        after_cast = slug in burst_resolves_after_cast
        burst_time = time + FULL_BURST_OPEN_DELAY if after_cast else time
        for _ in range(burst_hit_counts.get(slug, 1)):
            record(
                slug, percent, burst_time, "burst",
                damage_type=burst_damage_types.get(slug, "attack"),
            )

    def on_full_burst_enter(time, end):
        context.current_full_burst_end = end
        fire_trigger("full_burst_enter", rules_by_slug, context, registry, time)
        drain_instant_damage(time)

    def cdr_targets(pulse):
        if pulse.scope == "self":
            return [pulse.source_slug]
        if pulse.scope == "squad":
            return [m["slug"] for m in deck]
        if pulse.scope.startswith("element:"):
            element = pulse.scope.split(":", 1)[1]
            return [m["slug"] for m in deck if m["element"] == element]
        raise ValueError(f"unknown pulse scope: {pulse.scope}")

    def on_full_burst_end(time):
        fire_trigger("full_burst_end", rules_by_slug, context, registry, time)
        drain_instant_damage(time)
        context.burst_used_this_cycle.clear()
        reductions = {}
        for pulse in registry.drain_pulses("burst_cooldown_reduction_sec"):
            for slug in cdr_targets(pulse):
                reductions[slug] = reductions.get(slug, 0.0) + pulse.value
        return reductions

    # A Skill 1/2 with its own cooldown first fires at t=cooldown and repeats
    # (a universal battle-system rule, not at battle start). These rules apply
    # buffs/debuffs, which are INPUTS to damage - so unlike periodic_nukes (a
    # post-pass), they must populate the registry BEFORE the burst cycle
    # computes any nuke that should reflect them. Effects are replay-safe, so
    # pre-adding them at t=cooldown, 2*cooldown, ... is correct for every later
    # read. Fired against the initial context (no burst-cycle state yet), so
    # periodic rules must be stateless buff appliers.
    for slug, groups in periodic_rules.items():
        for cooldown, rules in groups:
            tick = cooldown
            while tick < fight_duration:
                for rule in rules:
                    if rule.condition(context, slug) and rule.time_condition(context, slug, tick):
                        rule.action(context, slug, tick, registry)
                tick += cooldown

    events = simulate_burst_cycle(
        deck,
        gauge_charge_time,
        fight_duration,
        mode,
        full_burst_duration_overrides=_stage_seconds(
            full_burst_stage_overrides, conditional_full_burst_deltas
        ),
        on_battle_start=on_battle_start,
        on_tier_fire=on_tier_fire,
        on_full_burst_enter=on_full_burst_enter,
        on_full_burst_end=on_full_burst_end,
    )

    # Full Burst windows [start, end) from the burst-cycle's own event log, so
    # a resource fill gated to "during Full Burst" (e.g. Soda's Golden Chip)
    # can filter shots against them without re-deriving burst timing itself.
    full_burst_windows = list(zip(
        (e["time"] for e in events if e["type"] == "full_burst_start"),
        (e["time"] for e in events if e["type"] == "full_burst_end"),
    ))
    context.full_burst_windows = full_burst_windows

    # 이번 패스가 받은 단계 테이블을 창에 붙여 context에 싣는다 - 창 길이와 단계가
    # 같은 패스 안에서 항상 같은 출처를 갖도록. per-shot 소비자(소다의 Beginner's
    # Rewards 넉)가 자기 샷이 속한 창의 자기 단계를 여기서 읽는다.
    context.full_burst_extension_stages = [
        (start, end, full_burst_stage_overrides.get(index, {}))
        for index, (start, end) in enumerate(full_burst_windows)
    ]

    # A buff a unit's own burst grants at an OFFSET from the burst, whose
    # duration may run "until that unit's NEXT own burst" rather than a fixed
    # number of seconds - Milk: Blooming Bunny's Embarrassment state, entered a
    # few seconds after her Overconfident immunity lapses and cleared only by
    # her next burst (Fienn, 2026-07-20).
    #
    # Resolved here rather than from an `own_burst_activate` rule because "until
    # the next own burst" is unknowable while the burst-cycle walk is still
    # running - the walk has not scheduled that burst yet. By this point
    # `context.burst_times` is complete. Placed BEFORE the shot loop so a buff
    # landed here is visible both to shot generation (max ammo / reload / cadence
    # callables) and to phase 2's damage bundles, unlike the resource-driven buff
    # passes further down which run after the timeline is already fixed.
    for slug, specs in (burst_anchored_buffs or {}).items():
        own_bursts = context.burst_times.get(slug, [])
        for spec in specs:
            offset = spec.get("offset", 0.0)
            for index, burst_time in enumerate(own_bursts):
                start = burst_time + offset
                if start >= fight_duration:
                    continue
                duration = spec["duration"]
                if duration == UNTIL_NEXT_OWN_BURST:
                    # The fight ending counts as the state's end, so the last
                    # window is trimmed rather than running past the sim.
                    next_burst = (
                        own_bursts[index + 1] if index + 1 < len(own_bursts) else fight_duration
                    )
                    duration = next_burst - start
                    if duration <= 0:
                        continue
                registry.add(
                    Effect(spec["stat"], spec["value"], spec["scope"], duration, slug),
                    applied_at=start,
                )

    def _crit_rate_at_for(target):
        """The owner's live crit rate at a time, clamped exactly as the damage
        path clamps it - so an expected-crit counter can never run faster than
        one crit per shot."""
        return lambda t: min(1.0, base_crit_rate + registry.total_for("crit_rate", target, t))

    shot_times_by_slug = {}
    ammo_rounds_by_slug = {}
    last_bullet_times_by_slug = {}

    def in_full_burst(time):
        return any(start <= time < end for start, end in full_burst_windows)

    # 시각 트리거 환급은 버스트 일정이 정해진 뒤에야 시각을 갖는다. 버스트 사이클은
    # 발사 시각을 보지 않으므로 여기서 이미 확정돼 있고, 아군에게 가는 환급도 이
    # 시점에 나눠 담을 수 있다.
    ammo_refills = resolve_ammo_refills(deck, events)

    for slug, weapon in weapon_stats.items():
        target = target_for(slug)
        # 큐브와 스킬에서 오는 탄약 환급을 이 인카운터에 맞게 확정한다 - 스킬 쪽은
        # 보스 원소가 조건일 수 있고, 그 정보는 덱을 조립하는 로스터가 아니라
        # 여기에만 있다.
        refunds = resolve_ammo_refunds(weapon, boss_element)
        # 창이 필요하다고 선언한 환급(`needs_own_burst_window`)은 레지스트리가
        # 만들 때는 버스트 일정을 몰라 `windows=()`로 왔다 - 이제 `events`에
        # 일정이 있으니 여기서 채운다(아르카나의 로테이션 재장전).
        refunds = tuple(
            replace(r, windows=resolve_ammo_refund_windows(slug, events))
            if r.needs_own_burst_window else r
            for r in refunds)
        weapon = {**weapon,
                  "ammo_refund": refunds,
                  "ammo_refills": ammo_refills.get(slug, ())}
        # 플랫 발수 버프("최대 장탄 수 ▲ 2발")는 여기서 이 유닛의 기본 장탄에
        # 대한 비율로 환산되어 퍼센트와 한 값으로 합쳐진다 - 발수는 무기마다
        # 다른 배율이 되므로 스탯 자체는 스쿼드 스코프로 두고 환산만 수신자
        # 쪽에서 한다.
        max_ammo_percent_at = lambda t, target=target, base=weapon["max_ammo"]: (
            max_ammo_percent_total(registry, target, t, base)
        )
        reload_speed_percent_at = lambda t, target=target: registry.total_for(
            "reload_speed_percent", target, t
        )
        attack_speed_percent_at = lambda t, target=target: registry.total_for(
            "attack_speed_percent", target, t
        )
        # 머신건은 탄창 앞머리에서 공칭 연사에 도달하기까지 예열을 한다
        # (attack_rate.MG_SPINUP). 그 예열 속도를 움직이는 스킬이 여기로 온다.
        heating_speed_percent_at = lambda t, target=target: registry.total_for(
            "mg_heating_speed_percent", target, t
        )
        charge_speed_percent_at = lambda t, target=target: registry.total_for(
            "charge_speed_percent", target, t
        )
        # "Caster-based" charge buffs hand over absolute SECONDS rather than a
        # percent of the recipient's own charge - see attack_rate's
        # charge_time_with_speed. Liberalio and Mana are the consumers.
        charge_time_reduction_sec_at = lambda t, target=target: registry.total_for(
            "charge_time_reduction_sec", target, t
        )
        # 스케줄 함수가 라이브 최대 장탄을 읽을 수 있게 이 슬러그용 조회를 노출한다
        # (Laplace: Ultimate Hero의 변신 창은 탄창을 다 비우는 시간이라 [최대 장탄
        # 수 증가]에 비례한다 - 상수로 박으면 육성 상태가 다른 유저에게 틀린 주기가
        # 나온다). 슬러그마다 덮어쓰므로 스케줄 함수 안에서만 유효하다.
        context.max_ammo_percent_at = max_ammo_percent_at
        schedule_fn = weapon_mode_schedules.get(slug)
        segments = schedule_fn(context, fight_duration) if schedule_fn is not None else []
        shot_records = generate_segmented_shots(
            weapon, segments, fight_duration,
            max_ammo_percent_at=max_ammo_percent_at,
            reload_speed_percent_at=reload_speed_percent_at,
            attack_speed_percent_at=attack_speed_percent_at,
            charge_speed_percent_at=charge_speed_percent_at,
            charge_time_reduction_sec_at=charge_time_reduction_sec_at,
            heating_speed_percent_at=heating_speed_percent_at,
        )
        shot_times = [r.time for r in shot_records]
        # What each shot ACCOUNTS for toward squad ammo-expended counters. A
        # pouch skill fires one bullet and books hundreds of rounds, and which
        # pouch skill is doing the spending depends on the Full Burst window.
        in_fb_rounds, outside_fb_rounds = ammo_rounds_per_shot.get(slug, (1.0, 1.0))
        ammo_rounds_by_slug[slug] = [
            in_fb_rounds if in_full_burst(t) else outside_fb_rounds for t in shot_times
        ]
        last_bullets = {r.time for r in shot_records if r.is_last_bullet}
        first_bullets = {r.time for r in shot_records if r.is_first_bullet}
        # Per-shot triggers count this unit's shots and fire at a threshold
        # ("after N": once at the Nth shot; "every N": at every Nth) or on
        # the shot that empties its magazine ("last_bullet", threshold
        # unused - gap #1's residual variant, e.g. Julia's Crescendo). The
        # window-gated modes ("every_during_full_burst" / "every_during_own_
        # status_window") count only shots inside a window before the "every
        # Nth" step, exactly like the same-named resource fills (gap #7 - a
        # buff/nuke fired directly on the in-window count, e.g. Soda's Lucky
        # Golden Chip, Asuka's Anti A.T. Field nuke). Their rules apply buffs
        # to the registry (seen by phase 2 at each shot's time) or emit an
        # instant_damage_percent pulse recorded as a per-shot nuke.
        # "every_n_critical_hits" counts EXPECTED crits rather than shots (EVE's
        # Unstable Energy) and "accumulate" counts neither - it sums a per-shot
        # quantity the unit supplies and fires at a threshold (Dorothy:
        # Serendipity's 80 pellets) - see their branches below. Rules must
        # be stateless and must not change shot generation (reload/ammo), which
        # is already fixed for this unit here.
        unit_per_shot = per_shot_rules.get(slug, [])
        last_bullet_times_by_slug[slug] = last_bullets
        # The window-gated modes fire on the same in-window shot times a
        # matching resource fill would pick, so reuse `_resource_fill_times`'
        # window filter. "every_during_full_burst" carries N in `threshold`;
        # "every_during_own_status_window" carries (N, window_duration).
        own_burst_times = context.burst_times.get(slug, [])
        window_fire_times = {}
        # every_during_segment/every_outside_segment are keyed on record
        # IDENTITY (shot_index), not shot_time: a magazine-type base weapon
        # (AR/MG/SMG/SG) resumes with a fresh magazine at the exact instant
        # an until_shots segment's last shot lands (attack_rate's documented
        # resume semantic), so the segment's last ShotRecord (in_segment=
        # True) and the resumed magazine's first ShotRecord (in_segment=
        # False) can share an identical `time`. Matching by time value would
        # make both records satisfy both modes at that instant, breaking the
        # in_segment flag's whole purpose - a structural guarantee that one
        # shot can never fire both (Task 8 fix).
        window_fire_indices = {}
        sequence_fires = {}
        for idx, (threshold, mode, _rules) in enumerate(unit_per_shot):
            if mode == "every_during_full_burst":
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_full_burst", threshold), shot_times,
                    core_hittable, fight_duration, full_burst_windows,
                ))
            elif mode == "every_outside_full_burst":
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_outside_full_burst", threshold), shot_times,
                    core_hittable, fight_duration, full_burst_windows,
                ))
            elif mode == "every_during_own_status_window":
                # An optional third element is the BURST PERIOD: the status is
                # granted by a resource the burst itself spends, so it only
                # returns every Nth burst (Neon: Vision Eye's Firepower Gauge -
                # 1st, 4th, 7th ...). Without it the window opens on every burst.
                n, window_duration, *burst_period = threshold
                anchors = own_burst_times[::burst_period[0]] if burst_period else own_burst_times
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_own_status_window", n, window_duration), shot_times,
                    core_hittable, fight_duration, full_burst_windows, anchors,
                ))
            elif mode == "cycle_from_own_burst_to_full_burst_end":
                first, period = threshold
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_cycle_from_own_burst_to_full_burst_end", first, period),
                    shot_times, core_hittable, fight_duration, full_burst_windows, own_burst_times,
                ))
            elif mode == "every_during_segment":
                seg_indices = [i for i, r in enumerate(shot_records) if r.in_segment]
                window_fire_indices[idx] = {
                    i for pos, i in enumerate(seg_indices) if (pos + 1) % threshold == 0}
            elif mode == "every_outside_segment":
                base_indices = [i for i, r in enumerate(shot_records) if not r.in_segment]
                window_fire_indices[idx] = {
                    i for pos, i in enumerate(base_indices) if (pos + 1) % threshold == 0}
            elif mode == "accumulate":
                # Every other mode COUNTS shots. This one accumulates a
                # per-shot QUANTITY and fires when it crosses a threshold -
                # Dorothy: Serendipity's Flash, "when hitting the target with
                # 80 pellets", where a shot is worth 10 pellets normally, 15
                # while her burst's "Number of pellets +5" is up, and 1 (+5)
                # for the 3 shots her own proc fixes the count at 1.
                #
                # The threshold is SUBTRACTED rather than reset, so the
                # overshoot carries into the next cycle. That is what makes a
                # second threshold at 2x land on every second fire of the
                # first (Flash's 160-pellet bullet, Fienn confirmed in-game
                # 2026-08-07) instead of drifting apart.
                #
                # `shots_since_fire` is passed because a rule cannot read its
                # OWN effect here: `round_buff_rule`'s grants only become
                # Effects in the second pass, after every unit's shot loop
                # (gap #9), while this counter has to run before it. None
                # means "has not fired yet", which a unit must not mistake for
                # the shot right after a fire.
                limit, increment_at = threshold
                total, last_fire_index = 0.0, None
                fires = set()
                for i, shot_time in enumerate(shot_times):
                    since = None if last_fire_index is None else i - last_fire_index - 1
                    total += increment_at(context, slug, shot_time, registry, since)
                    if total >= limit:
                        total -= limit
                        fires.add(i)
                        last_fire_index = i
                window_fire_indices[idx] = fires
            elif mode == "every_n_critical_hits":
                # This engine never rolls crit per hit - every hit's damage is
                # scaled by the expected crit factor - so there is no "was this
                # shot a crit" event to count. An "after N critical hits"
                # trigger is therefore counted in EXPECTED crits: each shot
                # contributes the unit's live crit rate at that instant, and the
                # rule fires each time the running total crosses N, carrying the
                # remainder forward. Reading the rate PER SHOT rather than once
                # at build time is the whole point - it is what lets deck crit
                # buffs move the trigger's cadence (Fienn, 2026-07-20: an
                # expected-value conversion is only acceptable if the deck's
                # crit buffs count). Caveat: shot loops run per unit, so a crit
                # buff applied by a LATER-processed ally's own per-shot rules is
                # not visible here; burst / full-burst-triggered crit buffs are,
                # since those rules run before any shot loop.
                crit_rate_at = _crit_rate_at_for(target)
                window_fire_indices[idx] = set(
                    _expected_crit_positions(shot_times, threshold, crit_rate_at)
                )
            elif mode == "sequence":
                # threshold carries the requirement spec; the rules slot holds
                # one rule list PER STAGE (see _sequence_fire_rules).
                sequence_fires[idx] = _sequence_fire_rules(
                    threshold, _rules, shot_times, own_burst_times
                )
        for shot_index, rec in enumerate(shot_records):
            shot_time = rec.time
            count = shot_index + 1
            for idx, (threshold, mode, rules) in enumerate(unit_per_shot):
                if mode == "sequence":
                    rules = sequence_fires[idx].get(shot_time, ())
                    fires = bool(rules)
                else:
                    fires = (
                        (mode == "after" and count == threshold)
                        or (mode == "every" and count % threshold == 0)
                        or (mode == "last_bullet" and shot_time in last_bullets)
                        or (mode == "first_bullet" and shot_time in first_bullets)
                        or (idx in window_fire_times and shot_time in window_fire_times[idx])
                        or (idx in window_fire_indices and shot_index in window_fire_indices[idx])
                    )
                if fires:
                    for rule in rules:
                        if (rule.condition(context, slug)
                                and rule.time_condition(context, slug, shot_time)):
                            rule.action(context, slug, shot_time, registry)
                    for pulse in registry.drain_pulses("instant_damage_percent"):
                        record(
                            pulse.source_slug, pulse.value, shot_time, "per_shot_nuke",
                            damage_type=pulse.damage_type,
                        )
            damage_type = rec.damage_type or normal_attack_type(slug, rec.weapon, shot_time)
            # A normal attack IS Full-Burst-Bonus eligible: its shot time is the
            # most concrete "computed later than the cast" there is, so the flag
            # just enables the engine's own window test against that shot's own
            # time. Measured (Fienn, 2026-07-28, Anis: Star + Ade + Liberalio at
            # target DEF 100): the same core non-crit shot reads 1,586,816
            # outside the window and 7,492,265 inside it, and the two hypotheses
            # differ by exactly (1 + 1.0 + 0.5) / (1 + 1.0) = 1.2500. The
            # measurement lands on the +0.5 branch to 0.00003%.
            record(slug, rec.damage_percent, shot_time, "normal_attack",
                   damage_type=damage_type, extra_charge_bonus=rec.extra_charge_bonus,
                   on_charge_weapon=rec.weapon in CHARGE_WEAPONS,
                   always_core_hit=rec.always_core_hit,
                   spread_diameter=rec.spread_diameter,
                   magazine_index=rec.magazine_index)
        shot_times_by_slug[slug] = shot_times

    # "For N round(s)" (bullet-count) buffs expire when the affected ally
    # fires N normal attacks, not after a fixed time. Turn each grant that
    # targets a unit into a concrete Effect whose window covers exactly its
    # next N shots after the grant (from the first covered shot up to the next
    # uncovered shot / fight end), so phase 2 applies the buff to precisely
    # those shots and nothing after. A squad grant is consumed independently
    # by each ally's own shots (one Effect per unit). Runs as a SECOND pass
    # after ALL units' shot loops (gap #9 refactor), so grants recorded by
    # per-shot rules - of this unit or a later-processed one - convert too;
    # burst-cycle-trigger grants (Zwei, Miranda) exist before any shot loop,
    # so their covering shots are unchanged by the move.
    for slug, shot_times in shot_times_by_slug.items():
        target = target_for(slug)
        windows = []  # (grant, start, end) for the grants hitting THIS unit
        for grant in registry.round_grants():
            if grant.scope == "self":
                covers_unit = grant.source_slug == slug
            else:
                covers_unit = _matches_scope(grant.scope, target)
            if not covers_unit:
                continue
            covered = [t for t in shot_times if t >= grant.granted_at][: grant.shots]
            if not covered:
                continue
            after_covered = [t for t in shot_times if t > covered[-1]]
            window_end = after_covered[0] if after_covered else fight_duration
            windows.append((grant, covered[0], window_end))
        for index, (grant, start, end) in enumerate(windows):
            if _round_grant_over_cap(index, grant, start, end, windows):
                continue
            registry.add(
                Effect(grant.stat, grant.value, f"slugs:{slug}", end - start, grant.source_slug),
                applied_at=start,
            )

    # Resolve quantity-based resources (battery / ammo pouch / N-stack counter).
    # Each spec's fill schedule is deterministic (here: +amount every Nth of the
    # owner's shots), so its count is a function of time (context.resource_count).
    # Each derived buff is emitted as a STEP FUNCTION over the fill/expiry events:
    # at each event we add a delta Effect (duration=None) carrying the change in
    # value, so total_for's running sum equals value_fn(count) at every time -
    # permanent stacks ramp up (all-positive deltas that plateau at the cap) and
    # timed stacks also come back down (negative deltas as they expire). Runs
    # after the shot loop so every fill is known; before phase 2, so
    # record-then-compute lets these buffs reach damage recorded earlier.
    for slug, specs in resource_specs.items():
        shot_times = shot_times_by_slug.get(slug, [])
        for spec in specs:
            if spec.fill[0] == "squad_burst_cycle_conditional":
                _resolve_squad_burst_cycle_resource(spec, slug, events, context)
                continue
            # A resource may be fed by several sources at different rates, each
            # granting its own amount (see _fill_sources).
            fill_times = []
            for source, amount in _fill_sources(spec.fill):
                source_times = _resource_fill_times(
                    source, shot_times, core_hittable, fight_duration, full_burst_windows,
                    context.burst_times.get(slug, []), last_bullet_times_by_slug.get(slug, set()),
                    crit_rate_at=_crit_rate_at_for(target_for(slug)),
                )
                for ft in source_times:
                    context.fill_resource(slug, spec.name, amount, ft)
                fill_times.extend(source_times)

            # Resets (a resource whose value is REPLACED rather than
            # incremented, e.g. Soda's Golden Chip starting at its 50 cap) are
            # collected from every reset spec and replayed in time order, so
            # each reset's pre-value correctly reflects fills AND any earlier
            # reset already applied. Each spec carries either a fixed `value`
            # or a `value_fn(pre_value)` for a consumption that reads the count
            # it is spending - e.g. Elegg's ghosts, spending 9 at the 13 cap
            # and 6 below it but never dropping under 1.
            reset_events = []
            for reset_spec in spec.resets:
                if reset_spec["trigger"] == "battle_start":
                    reset_events.append((0.0, reset_spec))
                elif reset_spec["trigger"] == "own_burst":
                    reset_events.extend((rt, reset_spec) for rt in context.burst_times.get(slug, []))
                elif reset_spec["trigger"] == "own_burst_delayed":
                    # Resets `reset_spec["delay"]` seconds AFTER each own-burst
                    # fire, not at the burst itself - e.g. Asuka's Anti A.T.
                    # Field, cleared when Annihilation State ends (9s later),
                    # not when the burst that started it fires.
                    delay = reset_spec["delay"]
                    reset_events.extend(
                        (rt + delay, reset_spec) for rt in context.burst_times.get(slug, [])
                    )
                elif reset_spec["trigger"] == "full_burst_end":
                    # Cleared when the squad's Full Burst ends, whoever opened
                    # it - e.g. Arcana: Fortune Mate's Happy Memories, removed
                    # there by Keepsake Album's own third bullet. Distinct from
                    # "own_burst_delayed" with a 10 sec delay, which lands one
                    # burst-ordering beat early and would cut the window's last
                    # shots short.
                    reset_events.extend((end, reset_spec) for _start, end in full_burst_windows)
                elif reset_spec["trigger"] == "computed":
                    # The owning module walks the shot timeline and hands back
                    # the spend times - the reset-side partner of the "computed"
                    # fill kind, for a resource that empties itself on reaching
                    # its cap rather than on any squad-level event. Both sides
                    # come from ONE walk in the module, so they cannot disagree
                    # about when the resource was spent.
                    reset_events.extend(
                        (rt, reset_spec) for rt in reset_spec["times"](shot_times)
                    )
                else:
                    raise ValueError(f"unknown resource reset trigger: {reset_spec['trigger']}")
            reset_events.sort(key=lambda e: e[0])
            for reset_time, reset_spec in reset_events:
                pre_value = context.resource_count(slug, spec.name, reset_time, spec.cap)
                value_fn = reset_spec.get("value_fn")
                post_value = value_fn(pre_value) if value_fn else reset_spec["value"]
                context.reset_resource(slug, spec.name, reset_time, pre_value, post_value)
            reset_times = [rt for rt, _ in reset_events]

            for buff in spec.buffs:
                # NOT `events` - that name holds simulate_burst_cycle's own
                # event log (read by _resolve_squad_burst_cycle_resource for
                # OTHER slugs' resources processed later in this same loop);
                # shadowing it here corrupted that log for any
                # squad_burst_cycle_conditional resource resolved afterward
                # in the same _simulate_raid_once pass (only surfaced once a deck
                # combined a buffed resource with one, e.g. Asuka + Maiden
                # sharing Burst 3 - see test_interaction_asuka_maiden_shared_burst_tier.py).
                buff_step_times = set(fill_times) | set(reset_times)
                if buff.lifetime is not None:
                    buff_step_times |= {
                        ft + buff.lifetime for ft in fill_times if ft + buff.lifetime < fight_duration
                    }
                prev_value = 0.0
                for event_time in sorted(buff_step_times):
                    count = context.resource_count(slug, spec.name, event_time, spec.cap, buff.lifetime)
                    value = buff.value_fn(count)
                    if value != prev_value:
                        registry.add(
                            Effect(buff.stat, value - prev_value, buff.scope, None, slug),
                            applied_at=event_time,
                        )
                        prev_value = value

    # A buff triggered by a resource's FILL events, landing on OTHER squad
    # members (gap #8 - e.g. Maiden's Blessings Upon You: "when MP is
    # replenished, affects all Electric Code allies except for self").
    # resource_gated_buffs (below) reads a count at the owner's burst; this
    # reacts to each fill itself. Refreshing: consecutive fills within the
    # duration refresh rather than stack (one source, NIKKE convention). Runs
    # after the resource_specs loop, so every fill is recorded by now; the
    # buffs are phase-2-visible like every other post-pass Effect.
    for slug, specs in resource_fill_triggered_buffs.items():
        for spec_index, spec in enumerate(specs):
            # One refresh group per spec: consecutive fills of THIS bullet
            # collapse, while the unit's other buffs on the same stat stand.
            refresh_group = f"resource_fill_{spec['resource']}_{spec_index}"
            if spec.get("condition") is not None and not spec["condition"](context, slug):
                continue
            targets = [m.slug for m in context.members if spec["member_filter"](m, slug)]
            if not targets:
                continue
            scope = "slugs:" + ",".join(targets)
            for fill_time, _amount in context.resource_fills.get((slug, spec["resource"]), []):
                for stat, value, duration in spec["buffs"]:
                    registry.add_refreshing(
                        Effect(stat, value, scope, duration, slug, refresh_group=refresh_group),
                        applied_at=fill_time,
                    )

    # A burst-fired buff gated on (or scaled by) a named resource's count AT
    # THE BURST'S OWN TIME - e.g. Soda's ATK+65.25%/15s if she had >=30 Golden
    # Chip stacks right before that same burst spent 17 of them. Processed
    # here (not at on_tier_fire, where the burst is actually recorded)
    # because the resource's fills/resets from the loop above aren't known
    # until now - same ordering reason as resource_scaled_nukes' deferred
    # percent, but a buff has no "phase 2" to defer to, so it's resolved here
    # instead, using context.burst_times (already recorded during the burst
    # cycle) for each of the owner's own burst-fire times.
    for slug, specs in resource_gated_buffs.items():
        for spec in specs:
            # Default read point is each of the owner's own burst fires. `"at":
            # "full_burst_end"` reads at every Full Burst's end instead - for a
            # buff whose skill text fires THERE while scaling off a resource
            # only the shot loop above could have filled (Arcana: Fortune Mate's
            # Keepsake Album, "when Full Burst ends ... x stack count of
            # Precious Moments"). A `full_burst_end` SkillRule cannot serve it:
            # those run inside the burst-cycle walk, long before any shot exists.
            if spec.get("at") == "full_burst_end":
                read_times = [end for _start, end in full_burst_windows]
            else:
                read_times = context.burst_times.get(slug, [])
            # `member_filter` resolves the scope against the LIVE squad (gap #3)
            # for a buff that names a weapon/element class rather than a fixed
            # target; `scope` stays for the fixed-target majority.
            if spec.get("member_filter") is not None:
                targets = [m.slug for m in context.members if spec["member_filter"](m, slug)]
                if not targets:
                    continue
                scope = "slugs:" + ",".join(targets)
            else:
                scope = spec["scope"]
            for read_time in read_times:
                if spec.get("use_pre_reset"):
                    count = context.resource_count_before_reset(slug, spec["resource"], read_time)
                    if count is None:
                        continue
                else:
                    count = context.resource_count(
                        slug, spec["resource"], read_time, spec["cap"], spec.get("lifetime")
                    )
                # `value_per_stack` scales with the count instead of gating on
                # it; a zero count then simply grants nothing.
                if spec.get("value_per_stack") is not None:
                    if count <= 0:
                        continue
                    value = spec["value_per_stack"] * count
                elif spec["gate_fn"](count):
                    value = spec["value"]
                else:
                    continue
                registry.add(
                    Effect(spec["stat"], value, scope, spec["duration"], slug),
                    applied_at=read_time,
                )

    # A burst-fired nuke whose HIT COUNT (not just its percent) is itself a
    # resource's value at burst time - e.g. Maiden's Diamond Dust, "attacks
    # repeatedly based on current MP". Reads the PRE-reset count (the resource
    # is drained by this same burst) at each of the owner's own burst times,
    # recording that many identical damage events. `extra_flat_atk_percent_of_
    # max_hp` (optional) adds a percentage of the owner's Max HP directly into
    # THIS nuke's own flat_atk term (e.g. "1372.8% of the sum of 10% Max HP and
    # ATK") without leaking into any other damage instance from the same slug.
    for slug, specs in dynamic_hit_count_nukes.items():
        for spec in specs:
            extra_flat_atk = spec.get("extra_flat_atk_percent_of_max_hp", 0.0) * base_stats[slug]["max_hp"]
            # `fire_delay` (optional): the nuke fires this many seconds AFTER
            # the burst, not at burst time itself - e.g. Asuka's Annihilation,
            # which lands when Annihilation State ends (9s later). The hit
            # count is read (and the resource reset, if any) at that same
            # delayed instant, matching `own_burst_delayed` above.
            delay = spec.get("fire_delay", 0.0)
            for burst_time in context.burst_times.get(slug, []):
                fire_time = burst_time + delay
                hit_count = context.resource_count_before_reset(slug, spec["resource"], fire_time)
                if hit_count is None:
                    continue
                # `hit_count_fn` (optional): the count picks the hit count
                # instead of being it - e.g. Elegg's 13 Ghosts, 13 sequential
                # hits at the 13-ghost cap and 6 hits below it.
                hit_count_fn = spec.get("hit_count_fn")
                if hit_count_fn:
                    hit_count = hit_count_fn(hit_count)
                for _ in range(int(hit_count)):
                    record(
                        slug, spec["base_percent"], fire_time, "dynamic_hit_count_nuke",
                        damage_type=spec.get("damage_type", "attack"), extra_flat_atk=extra_flat_atk,
                    )

    for slug, spec in periodic_nukes.items():
        required = spec.get("requires_part_destructible")
        if required is not None and required != context.part_destructible:
            continue
        cooldown = spec["cooldown"]
        percent = spec["percent"]
        damage_type = spec.get("damage_type", "attack")
        hit_count = spec.get("hit_count", 1)

        def _tick(tick_time, slug=slug, percent=percent, damage_type=damage_type,
                  hit_count=hit_count):
            for _ in range(hit_count):
                record(slug, percent, tick_time, "periodic", damage_type=damage_type)

        if spec.get("during_full_burst"):
            # Ticks only inside Full Burst windows, anchored to each window's
            # start (gap #6 - e.g. Ada Wong's Flash Grenade "every 2 sec during
            # Full Burst", Little Mermaid's Bubble Wave "every 1 sec only
            # during Full Burst"). own_burst_interval=(interval, duration):
            # a window starting inside [own burst, +duration) ticks at the
            # enhanced interval instead (Ada's post-burst "activation time
            # condition v 1 sec for 10 sec", Fienn 2026-07-16); her burst and
            # the FB start share ~the same instant, hence the <= comparison.
            own_interval = spec.get("own_burst_interval")
            own_bursts = context.burst_times.get(slug, [])
            for start, end in full_burst_windows:
                interval = cooldown
                if own_interval is not None and any(
                    bt <= start < bt + own_interval[1] for bt in own_bursts
                ):
                    interval = own_interval[0]
                tick = start + interval
                while tick < end:
                    _tick(tick)
                    tick += interval
        else:
            # The reduction is sampled once at the tick that starts each
            # step and fixes that step's whole length - not re-read as the
            # step plays out, so a buff lapsing partway through a step does
            # not split it; the step keeps running at the rate it started
            # with. Same shape as the during_full_burst branch above, which
            # fixes each window's interval from the state at the window's
            # start rather than tracking it continuously - acceptable here
            # for the same reason: the loop only needs a rate at the instant
            # it advances, not a sub-interval-accurate one.
            skill_slot = spec.get("cooldown_skill_slot")
            target = target_for(slug)
            tick = cooldown
            while tick < fight_duration:
                _tick(tick)
                factor = 1.0
                if skill_slot == 2:
                    reduction = registry.total_for(
                        "skill_cooldown_reduction_percent", target, tick)
                    factor = max(MIN_COOLDOWN_FACTOR, 1.0 - reduction)
                tick += cooldown * factor

    # Damage on a cadence the unit computes for itself. `periodic_nukes` covers
    # a fixed interval; a summoned entity whose attack rate depends on how many
    # of it are alive (Ein's Near Feathers) has a varying one. The schedule is
    # still deterministic - it falls out of the owner's burst times, which are
    # settled by now - so the unit module builds the time list and the engine
    # only emits it, keeping summon-lifetime bookkeeping out of the simulator.
    context.shot_times = shot_times_by_slug
    context.shot_ammo_rounds = ammo_rounds_by_slug
    for slug, specs in scheduled_nukes.items():
        for spec in specs:
            damage_type = spec.get("damage_type", "attack")
            # Optional `resource_gate` (same 4-tuple shape resource_scaled_nukes
            # uses): each tick's percent is scaled by a named resource's count
            # AT THAT TICK'S OWN TIME, resolved in phase 2. Lets a whole-fight
            # scheduled DoT scale off a stack counter - e.g. Mihara's Ensnaring
            # Chains, ticking every second at 25.08% PER stack.
            resource_gate = spec.get("resource_gate")
            for hit_time in spec["schedule"](context, fight_duration):
                if hit_time >= fight_duration:
                    continue
                record(slug, spec["percent"], hit_time, "scheduled",
                       damage_type=damage_type, resource_gate=resource_gate,
                       core_eligible_override=spec.get("core_eligible"))

    def _normal_attack_percent(ev):
        # Normal Attack Damage Multiplier is a Final ATK modifier on the
        # user's NORMAL ATTACKS only (damage-formula reference) - it scales
        # the shot's own coefficient, not any Damage-Up bucket, and touches
        # no other damage source.
        multiplier = 1 + _stat_bundle(ev["slug"], ev["time"])["normal_attack_damage_multiplier"]
        return _resolve_percent(ev) * multiplier

    # Phase 2: now that every buff/debuff is in the registry, compute each
    # recorded damage event against the final registry (each read at its own
    # time is replay-safe).
    def _entries(ev):
        """One damage entry per event - or TWO when a Pierce holder's normal
        attack strikes a core the boss keeps as a separate object from its body.
        The shot passes through the core and lands on the body behind it, and the
        body hit is the same instance minus the core bonus (Fienn, 2026-08-03).

        `hits_core` already folds in `core_hittable`, so the second instance
        cannot appear in a fight with no hittable core.
        """
        is_normal_attack = ev["source"] == "normal_attack"
        percent = _normal_attack_percent(ev) if is_normal_attack else _resolve_percent(ev)
        hits_core = core_hittable and (
            core_eligible(ev["source"], ev["damage_type"])
            if ev["core_eligible_override"] is None
            else ev["core_eligible_override"]
        )

        share = _core_hit_rate_at(ev["slug"], ev["time"], is_normal_attack,
                                  ev["always_core_hit"], ev["magazine_index"],
                                  ev["spread_diameter"])

        def instance(on_core, weight=1.0):
            return {
                "slug": ev["slug"],
                "time": ev["time"],
                "damage": _damage_instance(
                    ev["slug"], percent, ev["time"],
                    damage_type=ev["damage_type"],
                    extra_charge_bonus=ev["extra_charge_bonus"],
                    extra_flat_atk=ev["extra_flat_atk"],
                    hits_core=on_core,
                    core_hit_share=share,
                    on_charge_weapon=ev["on_charge_weapon"],
                    is_normal_attack=is_normal_attack,
                ) * weight,
                "source": ev["source"],
                "damage_type": ev["damage_type"],
            }

        pierces = (
            pierce_hits_body_behind_core
            and hits_core
            and is_normal_attack
            and _stat_bundle(ev["slug"], ev["time"])["has_pierce"] > 0
        )
        # The body hit keeps `source` = "normal_attack", so a caller's
        # burst/normal/skill split (deck_search._summarize) still adds up.
        #
        # 코어를 놓친 발은 본체에 맞고 그대로 나가므로 뚫고 나갈 코어가 없다.
        # 그래서 본체 인스턴스는 코어를 맞춘 비율만큼만 존재한다.
        return ([instance(True), instance(False, weight=share)] if pierces
                else [instance(hits_core)])

    damage_log = [entry for ev in damage_events for entry in _entries(ev)]

    result = {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
    if target_grants is not None:
        result["target_grants"] = target_grants
    return result, _resolve_conditional_fb_deltas(
        context, events, conditional_full_burst_deltas)


# `inspect.signature` follows `__wrapped__`, so introspecting the public name
# yields the real parameter list rather than the wrapper's (*args, **kwargs).
# Set here rather than beside the wrapper because `_simulate_raid_once` is
# defined below it.
#
# One entry in that list is not a real parameter for a caller: the wrapper
# supplies `full_burst_stage_overrides` itself on every iteration
# (`_simulate_raid_once(deck, **kwargs, full_burst_stage_overrides=overrides)`),
# so passing it through `simulate_raid(**kwargs)` raises `TypeError: got
# multiple values for keyword argument`. The advertised signature is honest
# about every other parameter.
simulate_raid.__wrapped__ = _simulate_raid_once
