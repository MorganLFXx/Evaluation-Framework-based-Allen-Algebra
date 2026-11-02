from generate.hint import *
import generate.hint as hint
from utils.relation import allen_relations


def get_negation(rel: str, l_no: int, r_no: int, events: list) -> list:
    event_l = events[l_no]
    event_r = events[r_no]
    explanation = hint.EXPLANATION_TEMPLATES[rel].format(
        event_l=event_l, event_r=event_r
    )
    return [
        {
            "hint": f"It is not true that '{event_l}' {allen_relations[rel]} '{event_r}' .",
            "explanation": f"It is not true that {explanation}.",
        }
    ]


def get_relation_hint(rel: str, l_no: int, r_no: int, events: list) -> list:
    """Generate hints based on relation and event numbers"""
    event_l = events[l_no]
    event_r = events[r_no]
    template = random.choice(HINT_TEMPLATES[rel])
    hint_text = template.format(event_l=event_l, l_no=l_no, event_r=event_r, r_no=r_no)
    explanation_text = hint.EXPLANATION_TEMPLATES[rel].format(
        event_l=event_l, event_r=event_r
    )
    return {"hint": hint_text, "explanation": explanation_text}


def generate_neg_hints(path, events):
    """Generate negative hints for a given path and events"""
    neg_hints = []
    for rel in path["excluded"]:
        l_no = path["base_event"][0]
        r_no = path["base_event"][1]
        neg_hints.extend(get_negation(rel, l_no, r_no, events))
    return neg_hints


def generate_indirect_neg_hints(path, events):
    hints = []
    seen_attrs = set()
    target_rel = path["target"]
    l_no = path["base_event"][0]
    r_no = path["base_event"][1]

    for rel in path["excluded"]:
        attrs = hint.pick_discriminating_attributes(target_rel, rel)
        for attr in attrs:
            if attr in seen_attrs:
                continue
            hint_info = hint.build_attribute_hint(target_rel, attr, events, l_no, r_no)
            if hint_info:
                seen_attrs.add(attr)
                hints.append(hint_info)
    return hints


def generate_indirect_evidence(path, events):
    hints = []
    target_rel = path["target"]
    l_no = path["base_event"][0]
    r_no = path["base_event"][1]

    def _select_attrs(target_rel, excluded_rels):
        core_attrs = hint.get_core_attributes(target_rel)
        if len(excluded_rels) == 0:
            return core_attrs

        target_def = hint.RELATION_DEFINITIONS[target_rel]
        remaining = set(excluded_rels)
        selected = []

        def differs(rel, attr):
            return hint.RELATION_DEFINITIONS[rel][attr] != target_def[attr]

        while remaining and len(selected) < len(core_attrs):
            best_attr = None
            best_removed = set()
            for attr in core_attrs:
                if attr in selected:
                    continue
                removed = {rel for rel in remaining if differs(rel, attr)}
                if len(removed) > len(best_removed):
                    best_removed = removed
                    best_attr = attr
            if not best_attr or not best_removed:
                break
            selected.append(best_attr)
            remaining -= best_removed

        if remaining:
            return core_attrs
        return selected

    attrs = _select_attrs(target_rel, path.get("excluded", []))
    for attr in attrs:
        hint_info = hint.build_attribute_hint(target_rel, attr, events, l_no, r_no)
        if hint_info:
            hints.append(hint_info)
    return hints


def generate_exclude_hint(excludes, l_no, r_no, events):
    """
    Args:
    - excludes: list of relations to exclude
    - l_no: left event number
    - r_no: right event number
    - events: list of event descriptions
    Return: a hint indicates relationships other than those to be excluded
    """
    candidate_funcs = []
    for attr, value_to_func in hint.ATTRIBUTE_HINT.items():
        excluded_values = {hint.RELATION_DEFINITIONS[rel][attr] for rel in excludes}
        for value, attr_func in value_to_func.items():
            # 特判: 如果要排除的关系的相对持续时间本就未知，那么使其持续关系已知不一定能引发冲突
            if excludes[-1] in ["p", "P", "m", "M", "o", "O"] and value in [
                Duration.SHORTER,
                Duration.LONGER,
                Duration.EQUAL,
            ]:
                continue
            if value not in excluded_values:
                candidate_funcs.append(attr_func)

    if not candidate_funcs:
        return None
    hint_info = random.choice(candidate_funcs)()

    return {
        "hint": hint_info["hint"].format(event_l=events[l_no], event_r=events[r_no]),
        "explanation": hint_info["explanation"].format(
            event_l=events[l_no], event_r=events[r_no]
        ),
    }


def generate_hint(path, events, hint_type):
    hints = []
    if path["left"] == -1:
        hints.append(
            get_relation_hint(
                path["path"][0], path["base_event"][0], path["new_event"], events
            )
        )
    if path["right"] == -1:
        hints.append(
            get_relation_hint(
                path["path"][1], path["new_event"], path["base_event"][1], events
            )
        )

    if hint_type == "direct neg":
        hints.extend(generate_neg_hints(path, events))
    elif hint_type == "indirect neg":
        hints.extend(generate_indirect_neg_hints(path, events))
    elif hint_type == "indirect pos":
        hints.extend(generate_indirect_evidence(path, events))
    return hints


# "direct neg", "indirect neg", "indirect pos"
def generate_hints(paths, events, hint_type="indirect pos"):
    hints = []
    for p in paths:
        p_hints = generate_hint(p, events, hint_type)
        hints.extend(p_hints)
    hint_texts = [h["hint"] for h in hints]
    explanations = [h["explanation"] for h in hints]
    return hint_texts, explanations


def main():
    path = {
        "target": "s",
        "path": ["s", "D"],
        "excluded": ["d", "D"],
        "parent": -1,
        "left": 2,
        "right": 1,
        "base_event": [0, 1],
        "new_event": 2,
    }

    hints = generate_hint(path, ["A", "B", "C", "D"], "indirect pos")
    print(hints)


if __name__ == "__main__":
    # main()
    print(1)