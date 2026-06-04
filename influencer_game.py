from __future__ import annotations

import argparse
import json
import operator
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


STAT_KEYS = (
    "mental",
    "reputation",
    "loyal_fan",
    "anti_fan",
    "fame",
    "network",
    "profit",
)

FINAL_ENDING_TIERS = (
    {
        "min_score": 80,
        "max_score": 100,
        "title": "시대의 아이콘",
        "image_key": "icon",
        "description": (
            "웬만한 A급 연예인을 훌쩍 뛰어넘는 거대한 팬덤과 파급력을 손에 쥐었습니다. "
            "메인 뉴스의 긍정적인 인터뷰 요청과 글로벌 브랜드의 초고액 앰버서더 제안이 쇄도합니다. "
            "수많은 위기를 기회로 바꾼 당신은 이제 인플루언서 생태계의 정점에 섰습니다."
        ),
    },
    {
        "min_score": 60,
        "max_score": 79,
        "title": "탄탄한 대기업 스트리머",
        "image_key": "stable_streamer",
        "description": (
            "숱한 위기를 무난하게 넘기며 고정 시청자층이 더욱 확고해졌습니다. "
            "단가 높은 광고가 안정적으로 들어오고, 매일 터지는 도네이션으로 수익은 이전과 비교할 수 없을 정도로 불어났습니다. "
            "인방 생태계의 굳건한 기득권으로 든든하게 자리 잡았습니다."
        ),
    },
    {
        "min_score": 40,
        "max_score": 59,
        "title": "쳇바퀴 도는 일상",
        "image_key": "routine",
        "description": (
            "무사히 나락을 피하며 일주일을 버텨냈지만, 채널의 상황은 사건이 터지기 전과 크게 달라지지 않았습니다. "
            "당장 굶어 죽진 않겠지만 언제 또 나락갈지 모른다는 불안감을 안고, "
            "당신은 한숨을 쉬며 오늘도 평소처럼 방송 켜기 버튼을 누릅니다."
        ),
    },
    {
        "min_score": 20,
        "max_score": 39,
        "title": "위태로운 줄타기",
        "image_key": "tightrope",
        "description": (
            "잘못된 대처들로 인해 대중의 시선은 차가워졌고 수익은 눈에 띄게 줄었습니다. "
            "하지만 다행히 채널이 완전히 폭파되지는 않았습니다. "
            "얼마 남지 않은 콘크리트 팬들을 붙잡고 뼈를 깎는 자숙과 노력을 거듭한다면, "
            "아주 먼 훗날 다시 회생할 일말의 가능성은 남아있습니다."
        ),
    },
    {
        "min_score": 0,
        "max_score": 19,
        "title": "완벽한 나락",
        "image_key": "downfall",
        "description": (
            "민심, 수익, 인맥... 그동안 쌓아왔던 모든 것이 산산조각 났습니다. "
            "더 이상 당신의 편을 들어주는 사람도, 믿고 맡길 스폰서도 남지 않았습니다. "
            "결국 당신은 쓸쓸히 은퇴 공지조차 남기지 못한 채, 방송계에서 영원히 퇴출당합니다."
        ),
    },
)

EARLY_ENDINGS = (
    {
        "stat": "mental",
        "op": "<=",
        "value": 0,
        "title": "멘탈 붕괴",
        "image_key": "mental_breakdown",
        "description": (
            "생방송 중 쏟아지는 비난을 견디지 못하고 이성을 잃은 채 오열하며 쓰러졌습니다. "
            "결국 폐쇄 병동에 입원하며 당신의 크리에이터 생명은 비극적으로 끝이 났습니다."
        ),
    },
    {
        "stat": "reputation",
        "op": "<=",
        "value": 0,
        "title": "평판 붕괴",
        "image_key": "reputation_collapse",
        "description": (
            "해명은 더 이상 아무에게도 닿지 않고, 대중은 당신의 모든 말을 의심하기 시작했습니다. "
            "신뢰가 완전히 무너진 채 댓글창과 커뮤니티에는 차가운 조롱만 남습니다."
        ),
    },
    {
        "stat": "profit",
        "op": "<=",
        "value": -80,
        "title": "파산 및 야반도주",
        "image_key": "bankruptcy_escape",
        "description": (
            "밀린 월세와 눈덩이처럼 불어난 위약금에 결국 스튜디오에 빨간 딱지가 붙었습니다. "
            "빚쟁이들을 피해 야반도주하며 채널의 시계는 영원히 멈췄습니다."
        ),
    },
    {
        "stat": "anti_fan",
        "op": ">=",
        "value": 100,
        "title": "플랫폼 영구 삭제",
        "image_key": "platform_ban",
        "description": (
            "안티팬들의 빗발치는 테러와 국민 청원에 플랫폼 본사마저 등을 돌렸습니다. "
            "'사회적 물의' 사유로 채널이 영구 삭제(Ban)되며 인터넷 방송계에서 쫓겨납니다."
        ),
    },
    {
        "stat": "network",
        "op": "<=",
        "value": 0,
        "title": "완벽한 고립과 은퇴",
        "image_key": "isolation_retirement",
        "description": (
            "업계 블랙리스트 1순위에 올라 동료와 스폰서 모두에게 철저히 외면당했습니다. "
            "완벽한 고립 속에서 허공에 혼자 떠들다 지쳐 쓸쓸히 은퇴를 선언합니다."
        ),
    },
    {
        "stat": "loyal_fan",
        "op": "<=",
        "value": 0,
        "title": "텅 빈 콘크리트",
        "image_key": "empty_fandom",
        "description": (
            "맹목적으로 당신을 감싸주던 마지막 찐팬마저 서늘한 작별 인사를 남기고 떠났습니다. "
            "아무도 없는 텅 빈 채팅창의 적막을 견디지 못하고 조용히 방송을 접습니다."
        ),
    },
    {
        "stat": "fame",
        "op": "<=",
        "value": 0,
        "title": "잊혀진 하꼬 자연사",
        "image_key": "forgotten_nobody",
        "description": (
            "아무리 자극적인 어그로를 끌어도 세상은 당신에게 티끌만 한 관심조차 주지 않습니다. "
            "차가운 무관심과 알고리즘의 외면 속에서 흔적도 없이 조용히 잊혀집니다."
        ),
    },
)


class ScenarioError(Exception):
    """Base class for game-related errors."""


class ScenarioLoadError(ScenarioError):
    """Raised when the JSON file cannot be loaded or has an invalid shape."""


class UnknownCharacterError(ScenarioError):
    """Raised when a character id does not exist."""


class InvalidChoiceError(ScenarioError):
    """Raised when a choice number is missing or out of range."""


class UnknownStatError(ScenarioError):
    """Raised when an event tries to modify an unsupported stat."""


class EventUnavailableError(ScenarioError):
    """Raised when an event is selected at the wrong time."""


@dataclass(frozen=True)
class StatChange:
    key: str
    label: str
    before: int
    requested_delta: int
    after: int

    @property
    def delta(self) -> int:
        return self.after - self.before

    def __str__(self) -> str:
        requested = ""
        if self.delta != self.requested_delta:
            requested = f", requested {self.requested_delta:+}"
        return f"{self.label}: {self.before} -> {self.after} ({self.delta:+}{requested})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "before": self.before,
            "delta": self.delta,
            "requested_delta": self.requested_delta,
            "after": self.after,
        }


class Stats:
    """Seven influencer stats. Profit can fall below zero for bankruptcy endings."""

    def __init__(
        self,
        values: dict[str, int],
        labels: dict[str, str] | None = None,
        min_value: int = 0,
        max_value: int = 100,
    ) -> None:
        self.labels = labels or {key: key for key in STAT_KEYS}
        self.min_value = min_value
        self.max_value = max_value
        self._values: dict[str, int] = {}

        for key in STAT_KEYS:
            if key not in values:
                raise ScenarioLoadError(f"Missing stat: {key}")
            self._values[key] = self._clamp(key, int(values[key]))

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Iterable[str]:
        return iter(STAT_KEYS)

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def __getitem__(self, key: str) -> int:
        if key not in self._values:
            raise UnknownStatError(f"Unknown stat: {key}")
        return self._values[key]

    def __setitem__(self, key: str, value: int) -> None:
        if key not in self._values:
            raise UnknownStatError(f"Unknown stat: {key}")
        self._values[key] = self._clamp(key, value)

    def __str__(self) -> str:
        return " | ".join(
            f"{self.labels.get(key, key)} {self._values[key]}" for key in STAT_KEYS
        )

    def _clamp(self, key: str, value: int) -> int:
        min_value = -100 if key == "profit" else self.min_value
        return max(min_value, min(self.max_value, value))

    @property
    def controversy_score(self) -> int:
        raw_score = (
            self["mental"]
            + self["reputation"]
            + self["loyal_fan"]
            + self["fame"]
            + self["network"]
            + self["profit"]
            + (100 - self["anti_fan"])
        ) / 7
        return max(0, min(100, int(raw_score + 0.5)))

    def apply(self, effects: dict[str, int]) -> list[StatChange]:
        changes: list[StatChange] = []
        for key, delta in effects.items():
            before = self[key]
            self[key] = before + int(delta)
            changes.append(
                StatChange(
                    key=key,
                    label=self.labels.get(key, key),
                    before=before,
                    requested_delta=int(delta),
                    after=self[key],
                )
            )
        return changes

    def copy(self) -> "Stats":
        return Stats(self._values.copy(), self.labels.copy(), self.min_value, self.max_value)

    def to_dict(self) -> dict[str, int]:
        return self._values.copy()

    def labeled_dict(self) -> dict[str, dict[str, Any]]:
        return {
            key: {"label": self.labels.get(key, key), "value": self._values[key]}
            for key in STAT_KEYS
        }


@dataclass
class Character:
    id: str
    name: str
    channel: str
    description: str
    intro: str
    stats: Stats

    def __str__(self) -> str:
        return f"{self.name} ({self.channel})"

    def copy(self) -> "Character":
        return Character(
            id=self.id,
            name=self.name,
            channel=self.channel,
            description=self.description,
            intro=self.intro,
            stats=self.stats.copy(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "channel": self.channel,
            "description": self.description,
            "intro": self.intro,
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_json(
        cls, character_id: str, raw: dict[str, Any], labels: dict[str, str]
    ) -> "Character":
        return cls(
            id=character_id,
            name=raw["name"],
            channel=raw["channel"],
            description=raw.get("description", ""),
            intro=raw.get("intro", ""),
            stats=Stats(raw["stats"], labels),
        )


@dataclass(frozen=True)
class Choice:
    text: str
    result: str
    effects: dict[str, int]
    set_flags: dict[str, bool]

    def __len__(self) -> int:
        return len(self.effects)

    def __bool__(self) -> bool:
        return bool(self.effects or self.set_flags)

    def __str__(self) -> str:
        return self.text

    def apply(self, character: Character, flags: dict[str, bool]) -> list[StatChange]:
        changes = character.stats.apply(self.effects)
        flags.update(self.set_flags)
        return changes

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "result": self.result,
            "effects": self.effects.copy(),
            "set_flags": self.set_flags.copy(),
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "Choice":
        return cls(
            text=raw["text"],
            result=raw.get("result", ""),
            effects={key: int(value) for key, value in raw.get("effects", {}).items()},
            set_flags={key: bool(value) for key, value in raw.get("set_flags", {}).items()},
        )


class Condition:
    OPS = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
    }

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw

    def __str__(self) -> str:
        if "all" in self.raw:
            return " and ".join(str(Condition(item)) for item in self.raw["all"])
        return f"{self.raw['stat']} {self.raw['op']} {self.raw['value']}"

    def matches(self, stats: Stats) -> bool:
        if "all" in self.raw:
            return all(Condition(item).matches(stats) for item in self.raw["all"])

        stat = self.raw["stat"]
        op = self.raw["op"]
        value = int(self.raw["value"])

        if op not in self.OPS:
            raise ScenarioLoadError(f"Unsupported condition operator: {op}")
        return self.OPS[op](stats[stat], value)

    def to_dict(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.raw, ensure_ascii=False))


@dataclass
class EventResult:
    event_id: str
    event_title: str
    category: str
    result_text: str
    changes: list[StatChange]
    flags: dict[str, bool]
    choice_text: str | None = None

    def __str__(self) -> str:
        lines = [f"[{self.event_title}]", self.result_text or "No result text."]
        if self.changes:
            lines.append("Changes:")
            lines.extend(f"- {change}" for change in self.changes)
        if self.flags:
            lines.append("Flags: " + ", ".join(f"{k}={v}" for k, v in self.flags.items()))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_title": self.event_title,
            "category": self.category,
            "choice_text": self.choice_text,
            "result_text": self.result_text,
            "changes": [change.to_dict() for change in self.changes],
            "flags": self.flags.copy(),
        }


@dataclass(frozen=True)
class EndingSummary:
    score: int
    title: str
    description: str
    min_score: int
    max_score: int
    kind: str = "final"
    condition: str = ""
    trigger_stat: str | None = None
    trigger_label: str | None = None
    trigger_value: int | None = None
    image_key: str = ""

    def __str__(self) -> str:
        label = "조기 종료" if self.kind == "early" else f"논란도 {self.score}점"
        return f"{label} [{self.title}]\n{self.description}"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "score": self.score,
            "논란도": self.score,
            "title": self.title,
            "description": self.description,
            "range": "" if self.kind == "early" else f"{self.min_score}-{self.max_score}",
            "kind": self.kind,
            "early": self.kind == "early",
            "image_key": self.image_key,
        }
        if self.kind == "early":
            payload.update(
                {
                    "condition": self.condition,
                    "trigger_stat": self.trigger_stat,
                    "trigger_label": self.trigger_label,
                    "trigger_value": self.trigger_value,
                }
            )
        return payload


def ending_for_score(score: int) -> EndingSummary:
    normalized = max(0, min(100, int(score)))
    for tier in FINAL_ENDING_TIERS:
        if tier["min_score"] <= normalized <= tier["max_score"]:
            return EndingSummary(
                score=normalized,
                title=tier["title"],
                description=tier["description"],
                min_score=tier["min_score"],
                max_score=tier["max_score"],
                image_key=tier["image_key"],
            )
    raise ScenarioError(f"Cannot resolve ending for score: {score}")


def early_ending_for_stats(stats: Stats) -> EndingSummary | None:
    ops = {
        "<=": operator.le,
        ">=": operator.ge,
    }
    for rule in EARLY_ENDINGS:
        stat = rule["stat"]
        value = stats[stat]
        target = int(rule["value"])
        op = rule["op"]
        if ops[op](value, target):
            label = stats.labels.get(stat, stat)
            return EndingSummary(
                score=stats.controversy_score,
                title=rule["title"],
                description=rule["description"],
                min_score=0,
                max_score=0,
                kind="early",
                condition=f"{label} {op} {target}",
                trigger_stat=stat,
                trigger_label=label,
                trigger_value=value,
                image_key=rule["image_key"],
            )
    return None


class Event:
    category = "event"

    def __init__(self, event_id: str, title: str, situation: str, choices: list[Choice] | None = None) -> None:
        self.id = event_id
        self.title = title
        self.situation = situation
        self._choices = choices or []

    def __len__(self) -> int:
        return len(self._choices)

    def __iter__(self) -> Iterable[Choice]:
        return iter(self._choices)

    def __getitem__(self, index: int) -> Choice:
        return self._choices[index]

    def __str__(self) -> str:
        return f"{self.title}\n{self.situation}"

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return self.id not in game.completed_event_ids

    def resolve(self, game: "ScenarioGame", choice_number: int | None = None) -> EventResult:
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "situation": self.situation,
            "category": self.category,
            "choices": [choice.to_dict() for choice in self._choices],
        }


class DecisionEvent(Event):
    category = "decision"

    def resolve(self, game: "ScenarioGame", choice_number: int | None = None) -> EventResult:
        choice = self._choice_by_number(choice_number)
        changed_flags = choice.set_flags.copy()
        changes = choice.apply(game.player, game.flags)
        return EventResult(
            event_id=self.id,
            event_title=self.title,
            category=self.category,
            choice_text=choice.text,
            result_text=choice.result,
            changes=changes,
            flags=changed_flags,
        )

    def _choice_by_number(self, choice_number: int | None) -> Choice:
        if choice_number is None:
            raise InvalidChoiceError(f"{self.title}: choice number is required.")
        try:
            index = int(choice_number) - 1
        except (TypeError, ValueError) as exc:
            raise InvalidChoiceError("Choice number must be an integer.") from exc
        if index < 0 or index >= len(self._choices):
            raise InvalidChoiceError(f"Choice must be between 1 and {len(self._choices)}.")
        return self._choices[index]


class ForcedEvent(Event):
    category = "forced"

    def __init__(self, event_id: str, title: str, situation: str, effects: dict[str, int]) -> None:
        super().__init__(event_id, title, situation, choices=[])
        self.effects = {key: int(value) for key, value in effects.items()}

    def resolve(self, game: "ScenarioGame", choice_number: int | None = None) -> EventResult:
        changes = game.player.stats.apply(self.effects)
        return EventResult(
            event_id=self.id,
            event_title=self.title,
            category=self.category,
            choice_text=None,
            result_text=self.situation,
            changes=changes,
            flags={},
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["effects"] = self.effects.copy()
        return payload


class MainEvent(DecisionEvent):
    category = "main"

    def __init__(
        self,
        event_id: str,
        title: str,
        situation: str,
        choices: list[Choice],
        character_id: str,
        day: int,
    ) -> None:
        super().__init__(event_id, title, situation, choices)
        self.character_id = character_id
        self.day = day

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return (
            super().is_available(game, day)
            and game.player.id == self.character_id
            and day == self.day
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update({"character_id": self.character_id, "day": self.day})
        return payload


class ChainDecisionEvent(DecisionEvent):
    category = "chain"

    def __init__(
        self,
        event_id: str,
        title: str,
        situation: str,
        choices: list[Choice],
        day: int,
        requires_flag: dict[str, bool] | None = None,
    ) -> None:
        super().__init__(event_id, title, situation, choices)
        self.day = day
        self.requires_flag = requires_flag or {}

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return (
            super().is_available(game, day)
            and day == self.day
            and _flags_match(game.flags, self.requires_flag)
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update({"day": self.day, "requires_flag": self.requires_flag.copy()})
        return payload


class ChainForcedEvent(ForcedEvent):
    category = "chain_forced"

    def __init__(
        self,
        event_id: str,
        title: str,
        situation: str,
        effects: dict[str, int],
        day: int,
        requires_flag: dict[str, bool] | None = None,
    ) -> None:
        super().__init__(event_id, title, situation, effects)
        self.day = day
        self.requires_flag = requires_flag or {}

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return (
            super().is_available(game, day)
            and day == self.day
            and _flags_match(game.flags, self.requires_flag)
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update({"day": self.day, "requires_flag": self.requires_flag.copy()})
        return payload


class RandomEvent(ForcedEvent):
    category = "random"

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return day in game.random_event_days


class TriggerEvent(DecisionEvent):
    category = "trigger"

    def __init__(
        self,
        event_id: str,
        title: str,
        situation: str,
        choices: list[Choice],
        condition: Condition,
    ) -> None:
        super().__init__(event_id, title, situation, choices)
        self.condition = condition

    def is_available(self, game: "ScenarioGame", day: int | None = None) -> bool:
        return (
            self.id not in game.triggered_event_ids
            and self.id not in game.completed_event_ids
            and self.condition.matches(game.player.stats)
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["condition"] = self.condition.to_dict()
        return payload


def _flags_match(flags: dict[str, bool], expected: dict[str, bool]) -> bool:
    return all(flags.get(key) is value for key, value in expected.items())


class ScenarioGame:
    random_event_days = {2, 3, 4, 5, 7}

    def __init__(
        self,
        title: str,
        stat_labels: dict[str, str],
        characters: dict[str, Character],
        main_events: list[MainEvent],
        random_events: list[RandomEvent],
        chain_events: list[Event],
        trigger_events: list[TriggerEvent],
    ) -> None:
        self.title = title
        self.stat_labels = stat_labels
        self.character_templates = characters
        self.main_events = main_events
        self.random_events = random_events
        self.chain_events = chain_events
        self.trigger_events = trigger_events
        self.player: Character | None = None
        self.flags: dict[str, bool] = {}
        self.history: list[EventResult] = []
        self.completed_event_ids: set[str] = set()
        self.triggered_event_ids: set[str] = set()
        self._rng = random.Random()

    def __len__(self) -> int:
        return len(self.character_templates)

    def __iter__(self) -> Iterable[Character]:
        return iter(self.character_templates.values())

    def __getitem__(self, character_id: str) -> Character:
        if character_id not in self.character_templates:
            raise UnknownCharacterError(f"Unknown character: {character_id}")
        return self.character_templates[character_id]

    def __str__(self) -> str:
        return f"{self.title} - {len(self)} characters"

    @classmethod
    def load(cls, path: str | Path) -> "ScenarioGame":
        source = Path(path)
        try:
            with source.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError as exc:
            raise ScenarioLoadError(f"JSON file not found: {source}") from exc
        except json.JSONDecodeError as exc:
            raise ScenarioLoadError(f"Invalid JSON format: {exc}") from exc
        except OSError as exc:
            raise ScenarioLoadError(f"Cannot read JSON file: {source}") from exc

        try:
            labels = data["stat_labels"]
            characters = {
                character_id: Character.from_json(character_id, raw, labels)
                for character_id, raw in data["characters"].items()
            }
            events = data["events"]
            return cls(
                title=data["game_title"],
                stat_labels=labels,
                characters=characters,
                main_events=_build_main_events(events["main"]),
                random_events=_build_random_events(events.get("random", [])),
                chain_events=_build_chain_events(events.get("chain", [])),
                trigger_events=_build_trigger_events(events.get("trigger", [])),
            )
        except KeyError as exc:
            raise ScenarioLoadError(f"Missing required JSON key: {exc}") from exc
        except TypeError as exc:
            raise ScenarioLoadError("JSON structure is not valid for this game.") from exc

    def select_character(self, character_id: str) -> Character:
        if character_id not in self.character_templates:
            raise UnknownCharacterError(f"Unknown character: {character_id}")

        self.player = self.character_templates[character_id].copy()
        self.flags.clear()
        self.history.clear()
        self.completed_event_ids.clear()
        self.triggered_event_ids.clear()
        return self.player

    def set_seed(self, seed: int | None) -> None:
        self._rng.seed(seed)

    def character_options(self) -> list[dict[str, Any]]:
        return [character.to_dict() for character in self.character_templates.values()]

    def events_for_day(self, day: int, include_random: bool = True) -> list[Event]:
        self._ensure_player()
        if self.is_early_game_over():
            return []

        events: list[Event] = []

        events.extend(event for event in self.main_events if event.is_available(self, day))
        events.extend(event for event in self.chain_events if event.is_available(self, day))

        available_random_events = [
            event for event in self.random_events if event.id not in self.completed_event_ids
        ]
        if include_random and day in self.random_event_days and available_random_events:
            events.append(self._rng.choice(available_random_events))

        return events

    def pending_triggers(self) -> list[TriggerEvent]:
        self._ensure_player()
        if self.is_early_game_over():
            return []
        return [event for event in self.trigger_events if event.is_available(self)]

    def apply_event(self, event: Event, choice_number: int | None = None) -> EventResult:
        self._ensure_player()
        if event.id in self.completed_event_ids:
            raise EventUnavailableError(f"Already completed event: {event.id}")

        result = event.resolve(self, choice_number)
        self.history.append(result)

        if isinstance(event, TriggerEvent):
            self.triggered_event_ids.add(event.id)
        self.completed_event_ids.add(event.id)

        return result

    @property
    def controversy_score(self) -> int:
        self._ensure_player()
        return self.player.stats.controversy_score

    def ending_summary(self) -> EndingSummary:
        self._ensure_player()
        early = self.early_ending()
        if early:
            return early
        return ending_for_score(self.controversy_score)

    def early_ending(self) -> EndingSummary | None:
        self._ensure_player()
        return early_ending_for_stats(self.player.stats)

    def is_early_game_over(self) -> bool:
        return self.early_ending() is not None

    def snapshot(self) -> dict[str, Any]:
        self._ensure_player()
        ending = self.ending_summary()
        return {
            "title": self.title,
            "character": self.player.to_dict(),
            "controversy_score": ending.score,
            "논란도": ending.score,
            "ending": ending.to_dict(),
            "game_over": self.is_early_game_over(),
            "flags": self.flags.copy(),
            "history": [result.to_dict() for result in self.history],
        }

    def _ensure_player(self) -> None:
        if self.player is None:
            raise UnknownCharacterError("Select a character first.")


def _build_choices(raw_choices: list[dict[str, Any]]) -> list[Choice]:
    return [Choice.from_json(raw) for raw in raw_choices]


def _build_main_events(raw_main: dict[str, dict[str, Any]]) -> list[MainEvent]:
    events: list[MainEvent] = []
    for character_id, days in raw_main.items():
        for day_text, raw in days.items():
            events.append(
                MainEvent(
                    event_id=raw["id"],
                    title=raw["title"],
                    situation=raw["situation"],
                    choices=_build_choices(raw["choices"]),
                    character_id=character_id,
                    day=int(day_text),
                )
            )
    return events


def _build_random_events(raw_random: list[dict[str, Any]]) -> list[RandomEvent]:
    return [
        RandomEvent(
            event_id=raw["id"],
            title=raw["title"],
            situation=raw["situation"],
            effects=raw.get("effects", {}),
        )
        for raw in raw_random
    ]


def _build_chain_events(raw_chain: list[dict[str, Any]]) -> list[Event]:
    events: list[Event] = []
    for raw in raw_chain:
        if raw.get("forced"):
            events.append(
                ChainForcedEvent(
                    event_id=raw["id"],
                    title=raw["title"],
                    situation=raw["situation"],
                    effects=raw.get("effects", {}),
                    day=int(raw["day"]),
                    requires_flag=raw.get("requires_flag", {}),
                )
            )
        else:
            events.append(
                ChainDecisionEvent(
                    event_id=raw["id"],
                    title=raw["title"],
                    situation=raw["situation"],
                    choices=_build_choices(raw["choices"]),
                    day=int(raw["day"]),
                    requires_flag=raw.get("requires_flag", {}),
                )
            )
    return events


def _build_trigger_events(raw_trigger: list[dict[str, Any]]) -> list[TriggerEvent]:
    return [
        TriggerEvent(
            event_id=raw["id"],
            title=raw["title"],
            situation=raw["situation"],
            choices=_build_choices(raw["choices"]),
            condition=Condition(raw["condition"]),
        )
        for raw in raw_trigger
    ]


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def print_event(event: Event) -> None:
    print("\n" + "=" * 70)
    print(f"{event.title} [{event.category}]")
    print("-" * 70)
    print(event.situation)
    for number, choice in enumerate(event, start=1):
        print(f"\n{number}. {choice.text}")


def ask_choice(max_choice: int) -> int:
    while True:
        answer = input(f"선택 번호를 입력하세요 (1-{max_choice}): ").strip()
        try:
            number = int(answer)
            if 1 <= number <= max_choice:
                return number
        except ValueError:
            pass
        print("올바른 번호를 입력해 주세요.")


def run_console(game: ScenarioGame) -> None:
    print(game)
    print("\n캐릭터를 선택하세요.")
    options = list(game)
    for number, character in enumerate(options, start=1):
        print(f"{number}. {character} / {character.stats}")

    character_number = ask_choice(len(options))
    player = game.select_character(options[character_number - 1].id)
    print(f"\n선택한 캐릭터: {player}")
    print(player.intro)

    for day in range(1, 8):
        print(f"\n\nDAY {day}")
        day_events = game.events_for_day(day)
        if not day_events:
            print("오늘은 큰 사건 없이 지나갑니다.")

        for event in day_events:
            print_event(event)
            choice_number = ask_choice(len(event)) if len(event) else None
            result = game.apply_event(event, choice_number)
            print("\n" + str(result))
            if game.is_early_game_over():
                print("\n조기 종료 엔딩")
                print(game.ending_summary())
                print("\n게임 종료")
                return

        triggers = game.pending_triggers()
        if triggers:
            trigger = triggers[0]
            print_event(trigger)
            result = game.apply_event(trigger, ask_choice(len(trigger)))
            print("\n" + str(result))
            if game.is_early_game_over():
                print("\n조기 종료 엔딩")
                print(game.ending_summary())
                print("\n게임 종료")
                return

        print(f"\n현재 스탯: {game.player.stats}")

    print("\n최종 엔딩")
    print(game.ending_summary())
    print("\n게임 종료")
    print(game.snapshot())


def run_sample(game: ScenarioGame) -> None:
    game.set_seed(7)
    player = game.select_character("sida_kim")
    print(f"Loaded: {game}")
    print(f"Selected: {player}")
    print(f"Stats count via __len__: {len(player.stats)}")

    event = game.events_for_day(1, include_random=False)[0]
    print_event(event)
    result = game.apply_event(event, 1)
    print("\n" + str(result))
    print(f"\nAfter sample choice: {player.stats}")
    print(game.ending_summary())


def main(argv: list[str] | None = None) -> int:
    configure_output_encoding()
    default_path = Path(__file__).with_name("scenario_final.json")
    if not default_path.exists():
        default_path = Path(__file__).with_name("scenario.json.json")
    parser = argparse.ArgumentParser(description="Influencer crisis survival game")
    parser.add_argument("json_path", nargs="?", default=default_path)
    parser.add_argument("--sample", action="store_true", help="Run a short non-interactive sample")
    args = parser.parse_args(argv)

    try:
        game = ScenarioGame.load(args.json_path)
        if args.sample:
            run_sample(game)
        else:
            run_console(game)
    except ScenarioError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
