import os
import argparse

def explore_and_read(base_path='./query-backend', depth=2):
    if not os.path.exists(base_path):
        print(f"❌ Path '{base_path}' not found.")
        return

    for root, dirs, files in os.walk(base_path):
        level = root.replace(base_path, '').count(os.sep)
        if level > depth:
            continue

        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")

        for f in files:
            file_path = os.path.join(root, f)
            ext = os.path.splitext(f)[1]

            if ext in ['.py', '.json', '.txt', '.env', '.md', ''] or f == 'Dockerfile':
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        print(f"\n{indent}📄 {f}:\n{'-' * 60}\n{content}\n{'-' * 60}\n")
                except Exception as e:
                    print(f"\n{indent}⚠️ Could not read {f}: {e}\n")
            else:
                print(f"{indent}📦 {f} [Skipped: binary or unsupported]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively explore and print contents of a directory"
    )
    parser.add_argument(
        "--base_path",
        "-p",
        default="./query-backend",
        help="Root directory to explore"
    )
    parser.add_argument(
        "--depth",
        "-d",
        type=int,
        default=2,
        help="Maximum depth to recurse"
    )
    args = parser.parse_args()
    explore_and_read(base_path=args.base_path, depth=args.depth)
