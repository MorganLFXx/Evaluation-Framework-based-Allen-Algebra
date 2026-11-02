import json
import os
import glob
import shutil
import random

from utils.chat import call_api, call_thinking_api
from utils.format import parse_json_block
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

allen_helper = """You are an expert in time relation judgment, well-versed in Allen's interval algebra.
This mathematical framework defines 13 fundamental types of temporal relationships：
precedes(p), preceded_by(P), meets(m), met_by(M), overlaps(o), overlapped_by(O), finished_by(F), finishes(f), contains(D), during(d), starts(s), started_by(S), equals(e).
Here are some things to note: 
1. 'A overlaps B' means that there is overlap between A and B but A starts before B. 'A overlapped_by B' means A and B still overlap, but B starts before A. 
2. 'A starts B' means A and B start at the same time but A ends before B. 'A started_by B' means A and B start at the same time but B ends before A.
3. 'A finishes B' means A and B end at the same time but A starts after B. 'A finished_by B' means A and B end at the same time but B starts after A.
The correspondence between uppercase and lowercase letters of the same letter is inverse. For example, A p B is equivalent to B P A.
Note: Allen relation can be converted to timeline. Each one indicates unique sequence of start and end time points for two events.
"""

post_question = """
For each hint, you should carefully consider how to interpret and only start reasoning after all hints have been interpreted. 
Output ONLY JSON with fields: \n
{
    "answer_single": "the abbreviation of the final answer. There is only one correct answer. But if you still have multiple answers and cannot decide, answer all of them. If you are unsure about more than five answers, just say 'I can not determine'.
}
Note: Just give the final answer(the abbreviation of the allen relation), don't explain how you get the answer.
"""

detail_post_question = """
For each hint, you must provide your interpretation. You should only start reasoning after all hints have been interpreted.
You should provide your thoughtfully considered thinking process, explaining how each hint influences your reasoning,
before finally answering with the abbreviations of final answer.
Output ONLY JSON with fields: \n
{
    "thinking": "Summary of your thoughtfully considered thinking process",
    "answer_single": "The abbreviation of the final answer. If you still have multiple answers and cannot decide, answer all of them."
}
Note: 
1. The 'thinking' field should divided into 2 parts: hint interpretation phase and reasoning phase. 
    - In hint interpretation phase, you should interpret basic meaning(the Allen relation, or relative length, or order of start and end points of the 2 events that can be judged.) of all hints one by one. (Remember "one by one")
    - In reasoning phase, you should provide thinking process bases on information from the hint interpretation phase.
2. In 'thinking' field, use '1. Hint Interpretation Phase: hint1: xxx, hint2: xxx, ... 2. Reasoning Phase: ...' format.
"""

post_question_conflict = """
Answer the number preceding the hint where you confirmed the existence of conflicts. If there are no conflicts, answer -1.
Output ONLY JSON with fields: \n
{
    "answer_single": "int-The number preceding the hint where you confirmed the existence of conflicts."
}
"""

detail_post_question_conflict = """
Answer the number preceding the hint where you confirmed the existence of conflicts. If there are no conflicts, answer -1.
Then compact your thoughtfully considered thinking process, including:
    - Provide your brief interpretation of each hint. 
    - Explain how you find the conflict, and why it is a conflict, before finally giving the answer.
Output ONLY JSON with fields: \n
{
    "thinking": "Summary of your thoughtfully considered thinking process",
    "answer_single": "int-The number preceding the hint where you confirmed the existence of conflicts."
}
Note: 
1. The 'thinking' field should divided into 2 parts: hint interpretation phase and reasoning phase. 
    - In hint interpretation phase, you should interpret basic meaning(the Allen relation, or relative length, or order of start and end points of the 2 events that can be judged.) of all hints one by one. 
    - In reasoning phase, you should provide thinking process bases on information from the hint interpretation phase.
2. In 'thinking' field, use '1. Hint Interpretation Phase: hint1: xxx, hint2: xxx, ... 2. Reasoning Phase: ...' format.
"""

post_question_fill = """
There are multiple possibilities for the missing hint; please provide only the most likely one.
You can use the format like:'Start(A)<Start(B)<End(A)=End(B)' or 'Start(A)<Start(B)<End(B)<End(A)' to describe the order of the start and end time points of the two events.(A and B are just placeholders)
Output ONLY JSON with fields: \n
{
    "answer_single": "The order of the start and end time points of the two events.'"
}
"""

detail_post_question_fill = """
There are multiple possibilities for the missing hint; please provide only the most likely one.
You should provide summary of your thoughtfully considered thinking process, including:
    - Provide your brief interpretation of each hint. 
    - Explain where the missing hint is and why, and how you get the answer, before finally giving the answer.
Output ONLY JSON with fields: \n
{
    "thinking": "Summary of your thoughtfully considered thinking process",
    "answer_single": "The order of the start and end time points of the two events.'"
}
Note: 
1. You can use the format like:'Start(A)<Start(B)<End(A)=End(B)' or 'Start(A)<Start(B)<End(B)<End(A)' to describe the order of the start and end time points of the two events.(A and B are just placeholders)
2. The 'thinking' field should divided into 2 parts: hint interpretation phase and reasoning phase. 
    - In hint interpretation phase, you should interpret basic meaning(the Allen relation, or relative length, or order of start and end points of the 2 events that can be judged.) of all hints one by one. 
    - In reasoning phase, you should provide thinking process bases on information from the hint interpretation phase.
3. In 'thinking' field, use '1. Hint Interpretation Phase: hint1: xxx, hint2: xxx, ... 2. Reasoning Phase: ...' format.
"""


def explain_extract(explanation):
    # "'{event_l}' equals '{event_r}' or Start({event_l})=Start({event_r})<End({event_l})=End({event_r}).", pattern
    # only extract the part after 'or'
    return explanation.split("or")[-1].strip()


def single_chat(sample, model):
    l = sample["target"]["l"]
    r = sample["target"]["r"]
    answers = []
    hints = sample["hints"]
    # random.shuffle(hints)
    explanation = sample["explanation"]
    question = (
        "Please help me determine the allen relationship between "
        f"'{sample['events'][l]}' and '{sample['events'][r]}' based on following information."
    )
    # question += post_question + "\n"
    question += detail_post_question + "\n"
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
        # if "Start(" in explanation[i] and "End(" in explanation[i]:
        #     question += f"{i+1}.{explain_extract(explanation[i])}\n"
        # else:
        #     question += f"{i+1}.{explanation[i]}\n"

    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]
    try:
        result = call_thinking_api(messages, model)
    except Exception as e:
        result = f"API调用失败{str(e)}"
    answers.append(result)
    sleep(1)
    return answers


def conflict_chat(sample, model):
    question = (
        "There is a conflict hint in the hints. "
        "Please help me find out the conflict hint."
        f"Note: All hints directly describe the relation between 2 events is absolutely correct."
        f"'Directly describe' means you can directly determine the allen relation(Or complete the sorting of four time points including the start and end times of two events) between 2 event based on this hint without any other hints. "
    )
    answers = []
    hints = sample["hints"]
    explanation = sample["explanations"]
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
        # if "Start(" in explanation[i] and "End(" in explanation[i]:
        #     question += f"{i+1}.{explain_extract(explanation[i])}\n"
        # else:
        #     question += f"{i+1}.{explanation[i]}\n"
    question += detail_post_question_conflict + "\n"
    # question += post_question_conflict + "\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]

    try:
        result = call_thinking_api(messages, model)
    except Exception as e:
        result = f"API调用失败{str(e)}"
    answers.append(result)
    sleep(1)
    return answers


def fill_chat(sample, model):
    answers = []
    l_no, r_no = sample["target"]["blank_object"]
    event_l, event_r = sample["events"][l_no], sample["events"][r_no]
    question = (
        f"Among these hints, there is one missing hint that describes the Allen relation between {event_l} and {event_r}."
        f"Based on the existing hints, please describe the order of the start and end time points of {event_l} and {event_r}."
    )
    explanation = sample["explanation"]
    hints = sample["hints"]
    # random.shuffle(hints)
    for i in range(len(hints)):
        question += f"{i+1}.{hints[i]}\n"
        # if "Start(" in explanation[i] and "End(" in explanation[i]:
        #     question += f"{i+1}.{explain_extract(explanation[i])}\n"
        # else:
        #     question += f"{i+1}.{explanation[i]}\n"
    question += detail_post_question_fill + "\n"
    # question += post_question_fill + "\n"
    messages = [
        {"role": "system", "content": allen_helper},
        {"role": "user", "content": question},
    ]

    try:
        result = call_thinking_api(messages, model)
    except Exception as e:
        result = f"API调用失败{str(e)}"
    answers.append(result)
    sleep(1)
    return answers


def infer_chat_type(sample):
    target = sample.get("target", {})
    if "conflict_no" in target:
        return "conflict"
    if "blank_object" in target:
        return "fill"
    return "single"


def process_sample(index, sample, chat_type, model):
    if (index + 1) % 5 == 0:
        print(f"== 正在处理第 {index + 1} 个用例 ==")
    if chat_type == "auto":
        chat_type = infer_chat_type(sample)
    if chat_type == "single":
        return single_chat(sample, model)
    if chat_type == "conflict":
        return conflict_chat(sample, model)
    if chat_type == "fill":
        return fill_chat(sample, model)
    raise ValueError(f"Unsupported chat_type: {chat_type}")


def _atomic_dump_json(path: str, data) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp_path, path)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _split_indices_contiguous(total: int, workers: int):
    """Split [0, total) into contiguous blocks.

    n = total // workers
    thread 0 -> [0, n)
    thread 1 -> [n, 2n)
    ...
    last thread -> [k*n, total)
    """
    if total <= 0:
        return []
    workers = max(1, workers)
    n = total // workers
    slices = []
    for worker_id in range(workers):
        start = worker_id * n
        end = (worker_id + 1) * n if worker_id < workers - 1 else total
        if start >= total:
            break
        if end < start:
            end = start
        slices.append((worker_id, start, end))
    return slices


def _recover_answers_from_temp(
    samples, answer_key: str, output_dir: str, name: str
) -> int:
    """Recover already-generated answers from per-thread temp files.

    Expected temp format (per line-item):
    - {"index": i, "sample": { ... , answer_key: ... }}
    - {"index": i, "skipped": true, "error": "..."}

    Only entries containing a valid `sample[answer_key]` are restored.
    """
    pattern = os.path.join(output_dir, f"{name}_*.json")
    paths = sorted(glob.glob(pattern))
    if not paths:
        return 0

    restored = 0
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if not isinstance(index, int) or not (0 <= index < len(samples)):
                continue
            sample_obj = item.get("sample")
            if not isinstance(sample_obj, dict):
                continue
            if answer_key not in sample_obj:
                continue

            samples[index][answer_key] = sample_obj[answer_key]
            restored += 1

    return restored


def answer_process(samples, index, answers, answer_key, thread_no):
    if isinstance(answers, str):
        samples[index][answer_key] = [answers]
    elif (
        isinstance(answers, list)
        and len(answers) > 0
        and hasattr(answers[0], "content")
    ):
        answer = answers[0].content
        if "thinking" in answer:
            answer = parse_json_block(answer)
            if answer is not None and "answer_single" in answer:
                samples[index][answer_key] = [answer.get("answer_single", "")]
            else:
                samples[index][answer_key] = ["I can not determine"]
            samples[index]["thinking"] = (
                answer.get("thinking", "") if answer is not None else ""
            )
        elif "answer_single" in answer:
            answer = parse_json_block(answer)
            if answer is not None and "answer_single" in answer:
                samples[index][answer_key] = [answer.get("answer_single", "")]
            else:
                samples[index][answer_key] = ["There is something error"]
        else:
            samples[index][answer_key] = [answer]
    else:
        print(
            f"  ⚠️ 线程 {thread_no} 处理第 {index + 1} 个用例时，答案格式不符合预期，已保存原始回答: {answers}"
        )


def multi_thread_generate(samples, name, chat_type, model, workers):
    # Special problem: temp directory deletion executed after the func, becauce this func can't persist data
    answer_key = f"answer_single"
    temp_dir = f"datasets/temp/{name}_{model}"
    _ensure_dir(temp_dir)

    # 从 temp 恢复已生成的答案（用于异常终止后的断点续跑）
    restored = _recover_answers_from_temp(samples, answer_key, temp_dir, name)
    if restored:
        print(f"已从temp恢复答案条目: {restored}")

    processed_indices = {
        index for index, sample in enumerate(samples) if answer_key in sample
    }
    if processed_indices:
        print(f"已存在答案的样本数: {len(processed_indices)} / {len(samples)}")

    total = len(samples)
    worker_count = max(1, workers)
    slices = _split_indices_contiguous(total, worker_count)
    if not slices:
        print("输入数据为空")
        return

    progress_lock = Lock()

    def worker_task(worker_id: int, start: int, end: int):
        thread_no = worker_id + 1
        thread_out_path = os.path.join(temp_dir, f"{name}_{thread_no}.json")
        thread_results = []

        # If file already exists, load it so we can continue appending.
        if os.path.exists(thread_out_path):
            try:
                with open(thread_out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if isinstance(existing, list):
                    thread_results = existing
            except Exception:
                thread_results = []

        print(f"线程 {thread_no} 负责区间: [{start}, {end})")

        for index in range(start, end):
            if index in processed_indices:
                continue

            try:
                answers = process_sample(index, samples[index], chat_type, model)
                with progress_lock:
                    answer_process(
                        samples=samples,
                        index=index,
                        answers=answers,
                        answer_key=answer_key,
                        thread_no=thread_no,
                    )
                    processed_indices.add(index)

                thread_results.append({"index": index, "sample": samples[index]})
                _atomic_dump_json(thread_out_path, thread_results)
            except Exception as e:
                print(
                    f"  ❌ 线程 {thread_no} 处理第 {index + 1} 个用例出错，已跳过: {e}"
                )
                thread_results.append(
                    {
                        "index": index,
                        "skipped": True,
                        "error": str(e),
                        "sample": samples[index],
                    }
                )
                _atomic_dump_json(thread_out_path, thread_results)
                continue

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(worker_task, worker_id, start, end)
            for worker_id, start, end in slices
            if end > start
        ]
        for future in as_completed(futures):
            future.result()


def main(name, chat_type, model, workers=1, hint="hint"):
    if not name:
        raise ValueError("name is required")
    if chat_type not in {"single", "conflict", "fill", "auto"}:
        raise ValueError("chat_type must be 'single', 'conflict', 'fill' or 'auto'")
    if hint not in {"hint", "story"}:
        raise ValueError("hint must be 'hint' or 'story'")
    temp_dir = f"datasets/temp/{name}_{model}"

    samples = json.load(open(f"datasets/{name}.json", "r"))
    multi_thread_generate(samples, name, chat_type, model, workers)

    final_path = f"datasets/answers/{name}_{model}_with_answers.json"
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)

    shutil.rmtree(temp_dir)

    print(f"Generated answers and saved to {final_path}")


if __name__ == "__main__":
    main(
        name="sample",
        chat_type="single",
        model="",
        workers=1,
        merge_only=False,
    )
