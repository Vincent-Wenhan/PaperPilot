"""Streamlit user interface for PaperPilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

import streamlit as st

from agents import DebugAgent, RunnerAgent
from config import MAIN_GOAL_DEBUG, OUTPUTS_DIR, PROJECT_ROOT
from main import run_paperpilot
from tools.llm_client import LLMClient


UPLOADS_DIR = PROJECT_ROOT / "uploads"
OUTPUT_FILES = (
    ("reproduction_plan.md", "下载 reproduction_plan.md", "text/markdown"),
    ("run.sh", "下载 run.sh", "text/x-shellscript"),
    ("report.md", "下载 report.md", "text/markdown"),
)
RUNNER_ENTRYPOINTS = (
    "train.py",
    "main.py",
    "eval.py",
    "test.py",
    "demo.py",
    "examples/demo.py",
)


def save_uploaded_pdf(uploaded_file: BinaryIO) -> Path:
    """Save one uploaded PDF under the project-local uploads directory."""
    original_name = Path(getattr(uploaded_file, "name", "paper.pdf")).name
    if Path(original_name).suffix.lower() != ".pdf":
        raise ValueError("仅支持上传 PDF 文件。")

    data = uploaded_file.getvalue()
    if not data:
        raise ValueError("上传的 PDF 文件为空。")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = "".join(
        character
        for character in Path(original_name).stem
        if character.isalnum() or character in {"-", "_"}
    )[:80]
    safe_stem = safe_stem or "paper"
    destination = UPLOADS_DIR / f"{uuid4().hex}_{safe_stem}.pdf"
    destination.write_bytes(data)
    return destination


def _show_pipeline_errors(errors: list[str]) -> None:
    if not errors:
        st.success("分析完成，未记录流程错误。")
        return
    st.warning("分析已完成，但部分步骤出现问题：")
    for error in errors:
        st.error(error)


def _show_outputs(result: dict[str, Any]) -> None:
    st.header("输出区")
    tabs = st.tabs(
        [
            "论文摘要",
            "方法拆解",
            "仓库分析",
            "环境配置",
            "实验计划",
            "run.sh",
            "report.md",
        ]
    )
    with tabs[0]:
        st.markdown(result.get("paper_info") or "尚未生成论文摘要。")
    with tabs[1]:
        st.markdown(result.get("method_info") or "尚未生成方法拆解。")
    with tabs[2]:
        repo_path = result.get("repo_path")
        if repo_path:
            st.caption(f"本地仓库：{repo_path}")
        st.markdown(result.get("repo_info") or "尚未生成仓库分析。")
    with tabs[3]:
        st.markdown(result.get("env_plan") or "尚未生成环境配置。")
    with tabs[4]:
        st.markdown(result.get("experiment_plan") or "尚未生成实验计划。")
    with tabs[5]:
        st.code(result.get("run_sh") or "尚未生成 run.sh。", language="bash")
    with tabs[6]:
        st.markdown(result.get("report") or "尚未生成 report.md。")


def _show_downloads() -> None:
    st.subheader("下载输出文件")
    columns = st.columns(len(OUTPUT_FILES))
    for column, (filename, label, mime) in zip(
        columns,
        OUTPUT_FILES,
        strict=True,
    ):
        path = OUTPUTS_DIR / filename
        with column:
            if path.is_file():
                st.download_button(
                    label=label,
                    data=path.read_bytes(),
                    file_name=filename,
                    mime=mime,
                    key=f"download_{filename}",
                )
            else:
                st.info(f"{filename} 尚未生成。")


def _debug_command_failure(command_result: dict[str, Any]) -> str:
    """Ask Debug Agent to diagnose one failed deterministic command."""
    try:
        return DebugAgent(LLMClient()).run(
            {
                "command": command_result.get("command", ""),
                "cwd": command_result.get("cwd", ""),
                "returncode": command_result.get("returncode"),
                "stdout": command_result.get("stdout", ""),
                "stderr": command_result.get("stderr", ""),
                "hardware": st.session_state.get(
                    "selected_hardware",
                    "未提供",
                ),
                "gpu_info": st.session_state.get(
                    "selected_gpu_info",
                    "未提供",
                ),
            }
        )
    except Exception as exc:
        return f"Debug Agent 执行失败：{exc}"


def execute_runner_command(
    command: str,
    cwd: str | Path,
    timeout: int = 120,
) -> tuple[dict[str, Any], str]:
    """Run an allowlisted command and automatically debug failures."""
    raw_result = RunnerAgent().run(
        {
            "command": command,
            "cwd": str(cwd),
            "timeout": timeout,
        }
    )
    try:
        command_result = json.loads(raw_result)
    except (TypeError, ValueError):
        command_result = {
            "command": command,
            "cwd": str(Path(cwd).resolve()),
            "returncode": None,
            "stdout": "",
            "stderr": raw_result,
            "success": False,
        }
    diagnosis = ""
    if not command_result.get("success", False):
        diagnosis = _debug_command_failure(command_result)
    return command_result, diagnosis


def _candidate_help_commands(repo_path: str) -> list[str]:
    """Return allowlisted help commands whose entrypoints actually exist."""
    if not repo_path:
        return []
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return []
    return [
        f"python {relative_path} --help"
        for relative_path in RUNNER_ENTRYPOINTS
        if (root / relative_path).is_file()
    ]


def _show_command_result(command_result: dict[str, Any]) -> None:
    st.write(f"Command: `{command_result.get('command', '')}`")
    st.write(f"CWD: `{command_result.get('cwd', '')}`")
    st.write(f"Return code: `{command_result.get('returncode')}`")
    st.text_area(
        "stdout",
        value=command_result.get("stdout", ""),
        height=140,
        disabled=True,
        key="runner_stdout",
    )
    st.text_area(
        "stderr",
        value=command_result.get("stderr", ""),
        height=140,
        disabled=True,
        key="runner_stderr",
    )


def _show_runner_section(result: dict[str, Any] | None) -> None:
    st.header("Runner 区")
    st.info(
        "Runner 只执行轻量安全命令，不会默认执行完整训练、下载大型数据集，"
        "也不会运行未知 shell 脚本。"
    )

    repo_path = str((result or {}).get("repo_path") or "")
    commands: list[tuple[str, str, Path]] = [
        ("运行 python --version", "python --version", PROJECT_ROOT),
        ("运行 pip --version", "pip --version", PROJECT_ROOT),
    ]
    commands.extend(
        (f"运行 {command}", command, Path(repo_path))
        for command in _candidate_help_commands(repo_path)
    )

    for index, (label, command, cwd) in enumerate(commands):
        if st.button(label, key=f"runner_command_{index}"):
            with st.spinner(f"正在安全运行：{command}"):
                command_result, diagnosis = execute_runner_command(
                    command,
                    cwd,
                )
            st.session_state["runner_result"] = command_result
            st.session_state["runner_debug_result"] = diagnosis

    if repo_path and not _candidate_help_commands(repo_path):
        st.caption("当前仓库未识别到可运行 `--help` 的候选入口文件。")
    elif not repo_path:
        st.caption("完成论文与仓库分析后，将显示已识别入口文件的 `--help` 按钮。")

    command_result = st.session_state.get("runner_result")
    if command_result:
        _show_command_result(command_result)
        if command_result.get("success"):
            st.success("命令执行成功。")
        else:
            st.error("命令执行失败或被安全策略拒绝。")

    diagnosis = st.session_state.get("runner_debug_result")
    if diagnosis:
        st.subheader("自动 Debug 结果")
        st.markdown(diagnosis)


def _show_debug_section() -> None:
    st.header("Debug 区")
    debug_log = st.text_area(
        "粘贴报错日志",
        height=220,
        placeholder="请粘贴运行命令、stdout、stderr 和环境信息。",
    )
    if st.button("分析报错", key="analyze_debug"):
        if not debug_log.strip():
            st.error("请先粘贴报错日志。")
            return
        with st.spinner("Debug Agent 正在分析报错"):
            try:
                diagnosis = DebugAgent(LLMClient()).run(
                    {
                        "error_log": debug_log,
                        "hardware": st.session_state.get(
                            "selected_hardware",
                            "未提供",
                        ),
                        "gpu_info": st.session_state.get(
                            "selected_gpu_info",
                            "未提供",
                        ),
                    }
                )
            except Exception as exc:
                diagnosis = f"Debug Agent 执行失败：{exc}"
        st.session_state["debug_result"] = diagnosis

    diagnosis = st.session_state.get("debug_result")
    if diagnosis:
        st.subheader("Debug Agent 诊断结果")
        st.markdown(diagnosis)


def main() -> None:
    """Render the PaperPilot Streamlit application."""
    st.set_page_config(
        page_title="PaperPilot：多智能体论文复现助手",
        layout="wide",
    )
    st.title("PaperPilot：多智能体论文复现助手")
    st.caption("从论文 PDF 与 GitHub 仓库生成可执行、可检查的复现计划。")

    st.header("输入区")
    uploaded_pdf = st.file_uploader("上传论文 PDF", type=["pdf"])
    github_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repository",
    )

    hardware_column, gpu_column, goal_column = st.columns(3)
    with hardware_column:
        hardware = st.selectbox(
            "硬件条件",
            ["CPU only", "Single GPU", "Multi GPU"],
        )
    with gpu_column:
        gpu_info = st.text_input("GPU 型号", placeholder="例如 RTX 4090")
    with goal_column:
        goal = st.selectbox(
            "复现目标",
            [
                "只理解论文",
                "跑通官方 demo",
                "最小训练实验",
                "复现主实验",
                MAIN_GOAL_DEBUG,
            ],
        )

    st.session_state["selected_hardware"] = hardware
    st.session_state["selected_gpu_info"] = gpu_info

    if st.button("Analyze", type="primary", key="analyze_pipeline"):
        # --- Debug goal: skip pipeline, go straight to Debug section ---
        if goal == MAIN_GOAL_DEBUG:
            st.info(
                "「Debug 报错」目标已选择。请滚动到页面底部的 Debug 区粘贴日志进行分析。"
            )
            st.session_state["debug_goal_selected"] = True
            st.session_state.pop("paperpilot_result", None)
        else:
            validation_errors: list[str] = []
            if uploaded_pdf is None:
                validation_errors.append("请先上传论文 PDF。")
            if not github_url.strip():
                validation_errors.append("GitHub URL 不能为空。")

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            else:
                try:
                    saved_pdf = save_uploaded_pdf(uploaded_pdf)
                except Exception as exc:
                    st.error(f"PDF 保存失败：{exc}")
                else:
                    st.session_state["uploaded_pdf_path"] = str(saved_pdf)
                    st.session_state.pop("debug_goal_selected", None)

                    # --- Real-time progress log ---
                    progress_container = st.container()
                    progress_log = progress_container.empty()
                    progress_lines: list[str] = []

                    def _on_progress(agent_name: str) -> None:
                        progress_lines.append(f"- {agent_name}...")
                        progress_log.markdown(
                            "**Agent 进度**\n" + "\n".join(progress_lines)
                        )

                    with st.status("Agent 状态区", expanded=True) as status:
                        _on_progress("初始化分析流程")
                        try:
                            result = run_paperpilot(
                                pdf_path=str(saved_pdf),
                                github_url=github_url.strip(),
                                hardware=hardware,
                                gpu_info=gpu_info.strip(),
                                goal=goal,
                                progress_callback=_on_progress,
                            )
                        except Exception as exc:
                            st.error(f"主流程执行失败：{exc}")
                            status.update(label="分析失败", state="error")
                        else:
                            st.session_state["paperpilot_result"] = result
                            _on_progress("分析完成")
                            status.update(label="Agent 流程完成", state="complete")

    result = st.session_state.get("paperpilot_result")
    if result:
        _show_pipeline_errors(result.get("errors", []))
        _show_outputs(result)
    elif st.session_state.get("debug_goal_selected"):
        st.info(
            "「Debug 报错」模式不运行主分析流程。请使用下方的 Debug 区。"
        )
    else:
        st.info("提交输入并点击 Analyze 后，将在此显示分析结果。")

    _show_downloads()
    _show_runner_section(result)
    _show_debug_section()


if __name__ == "__main__":
    main()
