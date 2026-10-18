"""容器执行器入口；尚无任务领取或模型能力。"""

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose", action="store_true", help="输出环境诊断后退出")
    args = parser.parse_args()
    if args.diagnose:
        print(
            json.dumps(
                {
                    "执行环境": "容器CPU",
                    "就绪": False,
                    "能力": [],
                    "说明": "任务执行器尚未实现",
                },
                ensure_ascii=False,
            )
        )
        return 0
    parser.exit(2, "任务执行器尚未实现，请使用 --diagnose 检查入口。\n")


if __name__ == "__main__":
    raise SystemExit(main())
