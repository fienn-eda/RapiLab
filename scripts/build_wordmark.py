"""앱 제목 워드마크를 폰트에서 SVG 아웃라인 컴포넌트로 구워낸다.

글자를 패스로 변환해 두면 산출물에 폰트 파일이 들어가지 않는다. 그래서
Daggersquare처럼 재배포가 금지된 폰트도 워드마크에 쓸 수 있다 - 1001Fonts FFC
라이선스는 폰트로 로고를 만드는 것은 명시적으로 허용하면서(§2), 폰트 파일을
게시하거나 다운로드로 제공하는 것은 금지한다(§5·§6). 자세한 근거는
docs/decisions.md를 볼 것.

산출물이 .svg가 아니라 .tsx인 이유는 프론트엔드에 SVG를 파일로 import하는
전례가 없기 때문이다. 인라인 JSX로 두면 빌드 설정도 타입 선언도 새로 필요하지
않고, fill="currentColor"가 살아 있어 색을 CSS가 정할 수 있다.

폰트 파일은 저장소에 없다. 실행하려면 직접 받아서 경로를 넘겨야 한다:

    https://www.1001fonts.com/daggersquare-font.html

지금 화면에 걸려 있는 것을 그대로 다시 만드는 명령:

    python scripts/build_wordmark.py \
        --font "<경로>/DAGGERSQUARE OBLIQUE.otf" \
        --weight 40 \
        --gradient "var(--text),var(--accent)"

기울기 10도는 --slant가 아니라 배포본 Oblique 파일 자체가 갖고 있다. 그 파일이
Regular를 정확히 10도 기울인 것이라(좌표 372개 비교, 최대 오차 0.81/1000 units)
Regular에 --slant 10을 줘도 같은 그림이 나오지만, 디자이너가 실제로 만든 파일을
쓰는 쪽을 택했다 - 폭 차이 0.01%는 배포본 좌표가 정수로 반올림된 결과다.
--slant는 10도가 아닌 각도를 원할 때 Regular에 걸면 된다.

--weight가 있는 이유는 이 글자꼴에 굵은 웨이트가 없기 때문이다 - 두 파일 다
weightClass 400이라 굵기는 획을 덧대어 합성한다.

워드마크 문자열·글자꼴·모양이 바뀔 때만 다시 돌리면 된다. 산출물은 저장소에
커밋되므로 평소 빌드에는 이 스크립트가 필요 없다.
"""

import argparse
import math
import sys
from pathlib import Path

try:
    from fontTools.misc.transform import Transform
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("ERROR: fontTools가 필요하다 - pip install fonttools")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "frontend" / "src" / "components" / "Wordmark.tsx"


def kern_pairs(font):
    """레거시 kern 테이블의 (왼쪽, 오른쪽) -> 조정값 딕셔너리.

    Daggersquare는 GPOS와 kern을 모두 싣고 있고 둘의 값이 같다. kern 쪽은
    셰이핑 엔진 없이 읽을 수 있어 이쪽을 쓴다. kern이 없는 폰트로 바꾸면
    커닝 없이 조판되므로 결과를 눈으로 확인할 것.
    """
    if "kern" not in font:
        return {}
    pairs = {}
    for table in font["kern"].kernTables:
        pairs.update(table.kernTable)
    return pairs


def layout(font, text):
    """각 글자의 글리프 이름과 시작 x좌표를 폰트 단위로 계산한다."""
    cmap = font.getBestCmap()
    widths = font["hmtx"].metrics
    pairs = kern_pairs(font)

    glyphs = []
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            sys.exit(f"ERROR: 폰트에 '{ch}' (U+{ord(ch):04X}) 글리프가 없다")
        glyphs.append(name)

    placed = []
    x = 0
    for i, name in enumerate(glyphs):
        placed.append((name, x))
        x += widths[name][0]
        if i + 1 < len(glyphs):
            x += pairs.get((name, glyphs[i + 1]), 0)
    return placed


def build_component(font_path, text, precision, component_name, slant, weight,
                    gradient):
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    placed = layout(font, text)

    # 폰트 좌표는 y가 위로 자라고 SVG는 아래로 자란다. 자리잡기·기울이기·y반전을
    # 행렬 하나로 합쳐 글리프마다 한 번씩만 통과시킨다. 기울이기가 y반전보다
    # 안쪽이어야 글자가 오른쪽으로 눕는다 - 순서를 바꾸면 왼쪽으로 눕는다.
    shear = Transform(1, 0, math.tan(math.radians(slant)), 1, 0, 0)

    def transform_for(x):
        return Transform(1, 0, 0, -1, 0, 0).transform(shear).translate(x, 0)

    bounds = BoundsPen(glyph_set)
    for name, x in placed:
        glyph_set[name].draw(TransformPen(bounds, transform_for(x)))
    if bounds.bounds is None:
        sys.exit("ERROR: 그려진 획이 없다 - 공백뿐인 문자열인가?")
    x_min, y_min, x_max, y_max = bounds.bounds

    pen = SVGPathPen(glyph_set, ntos=lambda v: f"{round(v, precision):g}")
    for name, x in placed:
        glyph_set[name].draw(TransformPen(pen, transform_for(x)))

    # 덧댄 획은 바깥쪽으로만 자라야 한다. paint-order로 fill을 stroke 위에
    # 올리면 안쪽 절반이 덮여 그렇게 된다. 다만 속공간은 그만큼 좁아지므로
    # 무한정 올릴 수 없다 - 세로기둥 132 units 기준 +90쯤에서 배가 메워진다.
    if weight:
        x_min -= weight / 2
        y_min -= weight / 2
        x_max += weight / 2
        y_max += weight / 2

    width = x_max - x_min
    height = y_max - y_min
    family = font["name"].getDebugName(4) or font["name"].getDebugName(1)
    designer = font["name"].getDebugName(8) or "unknown"
    view_box = f"{x_min:g} {y_min:g} {width:g} {height:g}"

    if gradient:
        start, end = gradient
        gradient_id = f"{component_name.lower()}-fill"
        paint = f"url(#{gradient_id})"
        defs = (f"      <defs>\n"
                f'        <linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">\n'
                f'          <stop offset="0%" stopColor="{start}" />\n'
                f'          <stop offset="100%" stopColor="{end}" />\n'
                f"        </linearGradient>\n"
                f"      </defs>\n")
        colour_note = (
            f"/** 앱 이름 워드마크. 높이는 CSS가 정하고, 색은 {start} -> {end}\n"
            f" *  그라디언트로 구워져 있다. */\n")
    else:
        paint = "currentColor"
        defs = ""
        colour_note = "/** 앱 이름 워드마크. 높이는 CSS가, 색은 currentColor가 정한다. */\n"

    stroke = ""
    if weight:
        stroke = (f' stroke="{paint}" strokeWidth="{weight:g}"'
                  f' strokeLinejoin="round" paintOrder="stroke"')

    # 기울기는 두 곳에서 온다 - 이 스크립트가 건 shear와, 애초에 기울어진 면을
    # 넘겼을 때 그 면이 갖고 있는 각도. 주석에는 합쳐서 적어야 오해가 없다.
    total_slant = slant - font["post"].italicAngle

    # aria-hidden인 이유는 이 글자꼴이 그림이기 때문이다. 읽히는 이름은 이
    # 컴포넌트를 감싸는 <h1>의 .visually-hidden 텍스트가 대고, 여기서 한 번 더
    # 이름을 내면 스크린 리더가 같은 단어를 두 번 읽는다.
    return (
        f"// GENERATED by scripts/build_wordmark.py - 손으로 고치지 말 것.\n"
        f"// 문구나 글자꼴을 바꾸려면 그 스크립트를 다시 돌린다.\n"
        f"//\n"
        f'// "{text}"를 {family} ({designer})로 기울기 {total_slant:g}도,\n'
        f"// 덧댄 획 {weight:g} units로 조판해 패스로 변환한 것이다. 이 글자꼴에는\n"
        f"// 굵은 웨이트가 없어 굵기는 획을 덧대어 합성한 것이다.\n"
        f"// 폰트 파일 자체는 재배포가 금지돼 있어 저장소에 없다 - 아웃라인만\n"
        f"// 남기면 배포물에 폰트가 들어가지 않는다. docs/decisions.md 참고.\n"
        f"\n"
        f"{colour_note}"
        f"export function {component_name}() {{\n"
        f"  return (\n"
        f'    <svg className="wordmark" viewBox="{view_box}" aria-hidden="true">\n'
        f"{defs}"
        f'      <path d="{pen.getCommands()}" fill="{paint}"{stroke} />\n'
        f"    </svg>\n"
        f"  )\n"
        f"}}\n"
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--font", required=True, type=Path,
                        help="워드마크를 조판할 .otf/.ttf 경로 (저장소에 없다)")
    parser.add_argument("--text", default="RapiLab", help="조판할 문자열")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"산출 컴포넌트 경로 (기본: {DEFAULT_OUT.relative_to(ROOT)})")
    parser.add_argument("--precision", type=int, default=1,
                        help="좌표 소수점 자리수 - 파일 크기와 정밀도의 절충")
    parser.add_argument("--slant", type=float, default=0.0, metavar="DEG",
                        help="오른쪽으로 눕히는 각도. Regular에 10을 주면 배포본 "
                             "Oblique와 좌표 오차 0.81/1000에서 일치한다")
    parser.add_argument("--weight", type=float, default=0.0, metavar="UNITS",
                        help="덧댈 획 두께 (폰트 units). 이 글자꼴은 굵은 웨이트가 "
                             "없어 굵기는 합성이다. 세로기둥이 132이라 40이 +30%%이고, "
                             "90쯤에서 속공간이 메워진다")
    parser.add_argument("--gradient", metavar="FROM,TO",
                        help="단색 대신 가로 그라디언트로 칠한다 (예: "
                             "'var(--text),var(--accent)'). 없으면 currentColor")
    args = parser.parse_args()

    gradient = None
    if args.gradient:
        parts = [p.strip() for p in args.gradient.split(",")]
        if len(parts) != 2 or not all(parts):
            sys.exit("ERROR: --gradient는 'FROM,TO' 두 색이어야 한다")
        gradient = tuple(parts)

    if not args.font.is_file():
        sys.exit(f"ERROR: 폰트 파일이 없다: {args.font}\n"
                 "       https://www.1001fonts.com/daggersquare-font.html 에서 받을 것")

    # 컴포넌트 이름은 파일명에서 따온다. 주변 컴포넌트가 모두 named export라
    # 이름과 파일명이 어긋나면 import가 조용히 어긋난다.
    component = build_component(args.font, args.text, args.precision, args.out.stem,
                                args.slant, args.weight, gradient)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(component, encoding="utf-8")
    print(f"wrote {args.out} ({len(component.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
