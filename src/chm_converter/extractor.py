"""CHM文件提取模块

使用7-Zip提取CHM文件中的HTML内容和资源文件
"""

import subprocess
from pathlib import Path
from typing import Dict, List


class CHMExtractor:
    """CHM文件提取器"""

    def __init__(self, seven_zip_cmd: str = "7z"):
        """
        初始化提取器

        Args:
            seven_zip_cmd: 7-Zip命令路径，默认为"7z"（假设在PATH中）
        """
        self.seven_zip_cmd = seven_zip_cmd

    def extract_chm(self, chm_path: str, output_dir: str) -> bool:
        """
        提取CHM文件到指定目录

        Args:
            chm_path: CHM文件路径
            output_dir: 输出目录

        Returns:
            是否提取成功
        """
        chm_path = Path(chm_path).resolve()
        output_dir = Path(output_dir).resolve()

        if not chm_path.exists():
            print(f"错误: CHM文件不存在: {chm_path}")
            return False

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"正在提取CHM文件: {chm_path.name}")
        print(f"输出目录: {output_dir}")

        try:
            # 使用7z提取文件
            # x: 提取文件保持目录结构
            # -o: 指定输出目录
            # -y: 自动回答yes
            cmd = [
                self.seven_zip_cmd,
                "x",
                str(chm_path),
                f"-o{output_dir}",
                "-y",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )

            if result.returncode == 0:
                print("✓ CHM文件提取成功")
                return True
            else:
                print("✗ CHM文件提取失败")
                print(f"错误信息: {result.stderr}")
                return False

        except FileNotFoundError:
            print(f"错误: 找不到7-Zip命令: {self.seven_zip_cmd}")
            print("请确保7-Zip已安装并添加到PATH环境变量")
            return False
        except Exception as e:
            print(f"错误: 提取CHM文件时出现异常: {e}")
            return False

    def list_files(self, chm_path: str, pattern: str = "*.htm*") -> List[str]:
        """
        列出CHM文件中的文件

        Args:
            chm_path: CHM文件路径
            pattern: 文件匹配模式，默认为"*.htm*"（匹配.html和.htm文件）

        Returns:
            文件路径列表
        """
        chm_path = Path(chm_path).resolve()

        if not chm_path.exists():
            print(f"错误: CHM文件不存在: {chm_path}")
            return []

        try:
            # 使用7z列出文件
            # l: 列出文件
            cmd = [self.seven_zip_cmd, "l", str(chm_path)]

            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )

            if result.returncode != 0:
                print("错误: 列出文件失败")
                return []

            # 解析输出，提取文件列表
            files = []
            in_file_list = False

            for line in result.stdout.split("\n"):
                # 跳过头部和尾部
                if "------------------- ----- ------------ ------------" in line:
                    in_file_list = not in_file_list
                    continue

                if in_file_list and line.strip():
                    # 文件行格式: Date Time Attr Size Compressed Name
                    parts = line.split()
                    if len(parts) >= 6:
                        filename = " ".join(parts[5:])
                        # 简单的模式匹配
                        if pattern == "*.htm*":
                            if filename.lower().endswith((".html", ".htm")):
                                files.append(filename)
                        else:
                            files.append(filename)

            return files

        except Exception as e:
            print(f"错误: 列出文件时出现异常: {e}")
            return []

    def get_html_files(self, extracted_dir: str) -> List[Path]:
        """
        获取提取目录中的所有HTML文件

        Args:
            extracted_dir: 提取后的目录

        Returns:
            HTML文件路径列表
        """
        extracted_dir = Path(extracted_dir)

        if not extracted_dir.exists():
            return []

        html_files = []
        for pattern in ["*.html", "*.htm"]:
            html_files.extend(extracted_dir.rglob(pattern))

        return sorted(html_files)

    def get_file_info(self, extracted_dir: str) -> Dict[str, int]:
        """
        获取提取目录的文件统计信息

        Args:
            extracted_dir: 提取后的目录

        Returns:
            文件统计信息字典
        """
        extracted_dir = Path(extracted_dir)

        if not extracted_dir.exists():
            return {}

        info = {
            "html_files": len(list(extracted_dir.rglob("*.htm*"))),
            "image_files": len(
                list(extracted_dir.rglob("*.png"))
                + list(extracted_dir.rglob("*.jpg"))
                + list(extracted_dir.rglob("*.jpeg"))
                + list(extracted_dir.rglob("*.gif"))
                + list(extracted_dir.rglob("*.svg"))
            ),
            "css_files": len(list(extracted_dir.rglob("*.css"))),
            "js_files": len(list(extracted_dir.rglob("*.js"))),
            "total_files": len(list(extracted_dir.rglob("*"))),
        }

        return info
