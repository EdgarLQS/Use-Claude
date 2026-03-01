#!/usr/bin/env python3
"""
一键提交脚本 - 快速提交并推送代码变更

功能：
1. 检查 git 状态并显示变更
2. 显示完整 diff 供用户审查
3. 自动生成提交信息并确认
4. 执行提交和推送
"""

import subprocess
import sys
from typing import List, Tuple, Optional


def run_command(command: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    """执行 shell 命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            capture_output=capture,
            text=True,
            check=False
        )
        return result
    except Exception as e:
        print(f"执行命令失败：{e}")
        sys.exit(1)


def check_git_status() -> Tuple[bool, str]:
    """检查 git 状态，返回是否有变更和状态输出"""
    result = run_command(["git", "status", "--short"])
    has_changes = bool(result.stdout.strip())
    return has_changes, result.stdout


def show_diff_stat() -> None:
    """显示变更统计摘要"""
    result = run_command(["git", "diff", "--stat"])
    if result.stdout:
        print("\n变更摘要:")
        print("-" * 50)
        print(result.stdout)
    else:
        # 检查是否有暂存的变更
        result = run_command(["git", "diff", "--stat", "--cached"])
        if result.stdout:
            print("\n暂存区变更摘要:")
            print("-" * 50)
            print(result.stdout)


def show_full_diff() -> None:
    """显示完整的 diff 内容"""
    result = run_command(["git", "diff"])
    staged_result = run_command(["git", "diff", "--cached"])

    if result.stdout:
        print("\n工作区变更详情:")
        print("=" * 50)
        print(result.stdout)

    if staged_result.stdout:
        print("\n暂存区变更详情:")
        print("=" * 50)
        print(staged_result.stdout)


def generate_commit_message() -> str:
    """根据变更内容生成建议的提交信息"""
    # 获取变更文件列表
    result = run_command(["git", "diff", "--name-only"])
    staged_result = run_command(["git", "diff", "--cached", "--name-only"])

    files = []
    if result.stdout:
        files.extend(result.stdout.strip().split("\n"))
    if staged_result.stdout:
        files.extend(staged_result.stdout.strip().split("\n"))

    files = [f for f in files if f]  # 过滤空行

    if not files:
        return "更新代码"

    # 分析变更类型
    commit_type = "feat"  # 默认
    all_diff = run_command(["git", "diff"]).stdout + run_command(["git", "diff", "--cached"]).stdout

    if any(kw in all_diff.lower() for kw in ["fix", "bug", "error", "exception", "crash"]):
        commit_type = "fix"
    elif any(kw in all_diff.lower() for kw in ["refactor", "clean", "restructure"]):
        commit_type = "refactor"
    elif any(kw in all_diff.lower() for kw in ["test", "spec"]):
        commit_type = "test"
    elif any(kw in all_diff.lower() for kw in ["doc", "readme", "comment"]):
        commit_type = "docs"
    elif any(kw in all_diff.lower() for kw in ["perf", "optim", "speed"]):
        commit_type = "perf"

    # 根据主要变更文件生成描述
    main_file = files[0] if files else "code"

    # 提取文件名（不含路径）
    filename = main_file.split("/")[-1].split("\\")[-1]

    # 生成提交信息
    description = f"更新 {filename}"

    # 尝试从 diff 中提取更多信息
    if "add" in all_diff.lower():
        description = f"添加 {filename} 功能"
    elif "remove" in all_diff.lower() or "delete" in all_diff.lower():
        description = f"移除 {filename} 中的代码"
    elif "update" in all_diff.lower() or "modify" in all_diff.lower():
        description = f"更新 {filename} 逻辑"

    return f"{commit_type}: {description}"


def confirm_commit(message: str) -> Optional[str]:
    """确认提交信息，允许用户修改"""
    print("\n建议的提交信息:")
    print("-" * 50)
    print(f"  {message}")
    print("-" * 50)
    print("\n选项:")
    print("  [Enter] 确认使用此提交信息")
    print("  [输入文字] 使用自定义提交信息")
    print("  [q] 取消提交")

    user_input = input("\n请确认：").strip()

    if user_input.lower() == "q":
        return None
    elif user_input:
        return user_input
    else:
        return message


def commit_changes(message: str) -> bool:
    """执行 git 提交"""
    # 添加所有变更
    print("\n正在添加变更...")
    add_result = run_command(["git", "add", "-A"])

    if add_result.returncode != 0:
        print(f"添加变更失败：{add_result.stderr}")
        return False

    print("已添加所有变更")

    # 创建提交
    print("正在创建提交...")
    commit_result = run_command(["git", "commit", "-m", message])

    if commit_result.returncode != 0:
        print(f"提交失败：{commit_result.stderr}")
        return False

    # 获取提交哈希
    hash_result = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit_hash = hash_result.stdout.strip()

    print(f"已创建提交 {commit_hash}: {message}")
    return True


def push_changes() -> bool:
    """推送到远程仓库"""
    print("\n正在推送到远程仓库...")

    # 检查是否有上游分支
    result = run_command(["git", "rev-parse", "--abbrev-ref", "--symbolic", "@{u}"], capture=True)

    if result.returncode != 0:
        # 没有上游分支，需要先设置
        branch_result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        current_branch = branch_result.stdout.strip()

        print(f"首次推送，设置上游分支为 origin/{current_branch}...")
        push_result = run_command(["git", "push", "-u", "origin", current_branch])
    else:
        push_result = run_command(["git", "push"])

    if push_result.returncode != 0:
        print(f"推送失败：{push_result.stderr}")
        return False

    print("推送成功")
    return True


def get_github_commit_url(commit_hash: str) -> Optional[str]:
    """获取 GitHub 提交链接"""
    # 获取远程仓库 URL
    result = run_command(["git", "remote", "get-url", "origin"])

    if result.returncode != 0:
        return None

    remote_url = result.stdout.strip()

    # 解析 GitHub URL
    if "github.com" in remote_url:
        # SSH 格式：git@github.com:user/repo.git
        if remote_url.startswith("git@"):
            parts = remote_url.replace(":", "/").split("/")
            user_repo = parts[1] + "/" + parts[2].replace(".git", "")
        # HTTPS 格式：https://github.com/user/repo.git
        else:
            parts = remote_url.replace("https://", "").split("/")
            user_repo = parts[1] + "/" + parts[2].replace(".git", "")

        return f"https://github.com/{user_repo}/commit/{commit_hash}"

    return None


def main() -> None:
    """主函数"""
    print("=" * 50)
    print("       一键提交脚本")
    print("=" * 50)

    # 1. 检查 git 状态
    print("\n正在检查 git 状态...")
    has_changes, status = check_git_status()

    if not has_changes:
        print("\n工作区是干净的，没有需要提交的变更")
        return

    # 2. 显示变更摘要
    show_diff_stat()

    # 3. 详细审查模式 - 显示完整 diff
    show_full_diff()

    # 4. 确认是否继续
    proceed = input("\n是否继续提交？[Y/n]: ").strip().lower()
    if proceed == "n":
        print("已取消提交")
        return

    # 5. 生成并提交确认信息
    suggested_message = generate_commit_message()
    final_message = confirm_commit(suggested_message)

    if final_message is None:
        print("已取消提交")
        return

    # 6. 执行提交
    if not commit_changes(final_message):
        return

    # 7. 推送
    if not push_changes():
        return

    # 8. 显示结果
    hash_result = run_command(["git", "rev-parse", "--short", "HEAD"])
    commit_hash = hash_result.stdout.strip()

    print("\n" + "=" * 50)
    print("提交成功!")
    print(f"  提交哈希：{commit_hash}")
    print(f"  提交信息：{final_message}")

    github_url = get_github_commit_url(commit_hash)
    if github_url:
        print(f"  查看提交：{github_url}")

    print("=" * 50)


if __name__ == "__main__":
    main()
