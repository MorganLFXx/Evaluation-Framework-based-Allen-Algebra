"""
entry for the whole project
the parse_args should be parsed here
"""

import argparse
import os

from generate import generate_data
from generate import generate_response
from generate import generate_sp_task
from explain import qa_checker
from explain import error_checker


def main():
    parser = argparse.ArgumentParser(description="Project entry point")
    subparsers = parser.add_subparsers(dest="command")

    data_parser = subparsers.add_parser("data", help="Generate data samples")
    data_parser.add_argument("--n", type=int, default=1, help="生成样例数量")
    data_parser.add_argument("--name", type=str, required=True, help="生成的文件名")
    data_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="样例递归深度，每基于target生成一次formula算一层",
    )
    data_parser.add_argument(
        "--type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="生成的任务类型",
        default="single",
    )

    response_parser = subparsers.add_parser("response", help="Generate responses")
    response_parser.add_argument(
        "--name", type=str, required=True, help="需要生成答案的文件名"
    )
    response_parser.add_argument(
        "--chat_type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="问题类型",
    )
    response_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行调用线程数",
    )
    response_parser.add_argument(
        "--model",
        type=str,
        help="调用的模型名称",
    )

    qa_parser = subparsers.add_parser("qa", help="QA checker utilities")
    qa_parser.add_argument(
        "--mode",
        type=str,
        choices=["answer_verify", "final_analyze"],
        default="answer_verify",
        help="运行模式",
    )
    qa_parser.add_argument("--name", type=str, help="校验的文件名")
    qa_parser.add_argument("--model", type=str, help="校验使用的模型名称")

    error_parser = subparsers.add_parser("error", help="Error checker utilities")
    error_parser.add_argument(
        "--path",
        required=True,
        help="Input dataset files or dataset names",
    )
    error_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行校验线程数",
    )
    error_parser.add_argument(
        "--model",
        type=str,
        default="qwen3.5-plus",
        help="Model name for call_api",
    )

    pipeline_parser = subparsers.add_parser("pipeline", help="Run the full pipeline")
    pipeline_parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Dataset name for the full pipeline",
    )
    pipeline_parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of samples to generate for the full pipeline",
    )
    pipeline_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Recursion depth for data generation in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers for response generation",
    )
    pipeline_parser.add_argument(
        "--chat_type",
        type=str,
        choices=["single", "conflict", "fill"],
        help="问题类型",
        default="single",
    )
    pipeline_parser.add_argument(
        "--model",
        type=str,
        default="deepseek-v3.2",
        help="Model name for response generation in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--check-model",
        type=str,
        default="qwen3.5-plus",
        help="Model name for answer verification in the full pipeline",
    )
    pipeline_parser.add_argument(
        "--skip-error-check",
        action="store_true",
        help="Whether to skip error checking in the full pipeline",
    )

    run_parser = subparsers.add_parser("run", help="Run an experiment from a YAML config")
    run_parser.add_argument("config", type=str, help="Path to the experiment YAML config")
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate the dataset even if it already exists",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the config, print resolved paths, run nothing",
    )
    run_parser.add_argument(
        "--stage",
        type=str,
        choices=["generate", "respond", "verify", "error_check"],
        help="Run only this single stage",
    )

    init_parser = subparsers.add_parser(
        "init", help="Interactively create an experiment YAML config"
    )
    init_parser.add_argument("--name", type=str, help="Experiment name")
    init_parser.add_argument(
        "--task", type=str, choices=["single", "conflict", "fill"], help="Task type"
    )
    init_parser.add_argument("--n", type=int, help="Number of samples")
    init_parser.add_argument("--depth", type=int, help="Recursion depth")
    init_parser.add_argument("--model", type=str, help="Response model")
    init_parser.add_argument("--check-model", type=str, help="Verification model")
    init_parser.add_argument("--workers", type=int, help="Parallel workers")
    init_parser.add_argument(
        "--stages", type=str, help="Comma-separated stage list (default: generate,respond,verify)"
    )
    init_parser.add_argument("--output", type=str, help="Output YAML path (default: <name>.yaml)")
    init_parser.add_argument(
        "--no-run", action="store_true", help="Write the config but do not run it"
    )

    args = parser.parse_args()
    if args.command == "data":
        generate_data.main(
            n=args.n,
            name=args.name,
            depth=args.depth,
            hint="indirect pos",
        )
        if args.type == "conflict":
            generate_sp_task.generate_conflict_task(args.name)
        if args.type == "fill":
            generate_sp_task.generate_fillblank_task(args.name)
    elif args.command == "response":
        generate_response.main(
            name=args.name,
            chat_type=args.chat_type,
            model=args.model,
            workers=args.workers,
            hint="hint",
        )
    elif args.command == "qa":
        if args.mode == "answer_verify":
            qa_checker.answer_verify(args.name)
        elif args.mode == "final_analyze":
            qa_checker.final_task_analyze(args.name, args.model)
        else:
            raise ValueError(f"Unsupported mode: {args.mode}")
    elif args.command == "error":
        error_checker.main(
            path=args.path,
            workers=args.workers,
            model=args.model,
        )
    elif args.command == "pipeline":
        # Task datasets are stored with a suffix (_conflict / _fillblank); the
        # base dataset is an intermediate artifact for the two special tasks.
        if args.chat_type == "conflict":
            dataset_name = f"{args.name}_conflict"
        elif args.chat_type == "fill":
            dataset_name = f"{args.name}_fillblank"
        else:
            dataset_name = args.name

        # 1. 数据生成(如果任务数据集已有则跳过)
        if not os.path.exists(f"datasets/{dataset_name}.json"):
            if not os.path.exists(f"datasets/{args.name}.json"):
                generate_data.main(
                    n=args.n,
                    name=args.name,
                    depth=args.depth,
                    hint="indirect pos",
                )
            if args.chat_type == "conflict":
                generate_sp_task.generate_conflict_task(args.name)
            elif args.chat_type == "fill":
                generate_sp_task.generate_fillblank_task(args.name)
        # 2. 回答生成
        generate_response.main(
            name=dataset_name,
            chat_type=args.chat_type,
            model=args.model,
            workers=args.workers,
            hint="hint",
        )
        # 3. 答案校验
        answers_name = f"{dataset_name}_{args.model}"
        right = qa_checker.answer_verify(answers_name)
        print(f"Answer verification completed. Correct answers: {right}")
        # 4. 错误校验(答案文件按 {dataset}_{model} 命名)
        if not args.skip_error_check:
            error_checker.main(
                path=answers_name,
                workers=max(
                    1, right // 8
                ),  # 根据正确率动态调整错误校验的线程数，避免过多线程导致API调用过快
                model=args.check_model,
            )
    elif args.command == "run":
        from runner import cli as runner_cli

        raise SystemExit(runner_cli.main_run(args))
    elif args.command == "init":
        from runner import cli as runner_cli

        raise SystemExit(runner_cli.main_init(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
