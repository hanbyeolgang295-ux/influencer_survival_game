from __future__ import annotations

import argparse
import json
import sys
import traceback
import uuid
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from influencer_game import Event, ScenarioError, ScenarioGame


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DEFAULT_SCENARIO = ROOT / "scenario_final.json"
MAX_DAY = 7
BOOT_LOG = ROOT / "web_server_boot.log"


def boot_log(message: str) -> None:
    try:
        with BOOT_LOG.open("a", encoding="utf-8") as file:
            file.write(message + "\n")
    except OSError:
        pass


class WebGameSession:
    def __init__(self, scenario_path: Path, seed: int | None = None) -> None:
        self.id = uuid.uuid4().hex
        self.game = ScenarioGame.load(scenario_path)
        self.game.set_seed(seed)
        self.day = 1
        self.event_queue: list[Event] = []
        self.last_result: dict[str, Any] | None = None

    def start(self, character_id: str) -> dict[str, Any]:
        self.game.select_character(character_id)
        self.day = 1
        self.event_queue = self.game.events_for_day(self.day)
        self.last_result = None
        return self.to_dict()

    def choose(self, choice_number: int | None) -> dict[str, Any]:
        event = self.current_event()
        if event is None:
            raise ScenarioError("진행할 이벤트가 없습니다.")

        result = self.game.apply_event(event, choice_number)
        self.last_result = result.to_dict()
        self.last_result["choice_number"] = choice_number

        if self.event_queue and self.event_queue[0].id == event.id:
            self.event_queue.pop(0)

        return self.to_dict()

    def next_day(self) -> dict[str, Any]:
        if self.game.is_early_game_over():
            return self.to_dict()
        if self.current_event() is not None:
            raise ScenarioError("현재 이벤트를 먼저 끝내야 합니다.")
        if self.day >= MAX_DAY:
            return self.to_dict()

        self.day += 1
        self.event_queue = self.game.events_for_day(self.day)
        self.last_result = None
        return self.to_dict()

    def current_event(self) -> Event | None:
        if self.game.is_early_game_over():
            return None
        if self.event_queue:
            return self.event_queue[0]

        triggers = self.game.pending_triggers()
        if triggers:
            return triggers[0]
        return None

    def to_dict(self) -> dict[str, Any]:
        current = self.current_event()
        early_game_over = self.game.is_early_game_over() if self.game.player else False
        can_advance = not early_game_over and current is None and self.day < MAX_DAY
        game_over = early_game_over or (current is None and self.day >= MAX_DAY)
        ending = self.game.ending_summary() if self.game.player else None

        return {
            "session_id": self.id,
            "title": self.game.title,
            "day": self.day,
            "max_day": MAX_DAY,
            "character": self.game.player.to_dict() if self.game.player else None,
            "flags": self.game.flags.copy(),
            "current_event": event_to_dict(current) if current else None,
            "can_advance": can_advance,
            "game_over": game_over,
            "controversy_score": ending.score if ending else None,
            "논란도": ending.score if ending else None,
            "ending": ending.to_dict() if ending else None,
            "last_result": self.last_result,
            "history": [result.to_dict() for result in self.game.history],
        }


def event_to_dict(event: Event) -> dict[str, Any]:
    payload = event.to_dict()
    payload["choice_required"] = len(event) > 0
    payload["choice_count"] = len(event)
    return payload


class GameServer:
    def __init__(self, scenario_path: Path) -> None:
        self.scenario_path = scenario_path
        self.sessions: dict[str, WebGameSession] = {}

    def new_session(self, character_id: str, seed: int | None = None) -> dict[str, Any]:
        session = WebGameSession(self.scenario_path, seed)
        self.sessions[session.id] = session
        return session.start(character_id)

    def get_session(self, session_id: str) -> WebGameSession:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise ScenarioError("세션을 찾을 수 없습니다. 새 게임을 시작해 주세요.") from exc

    def metadata(self) -> dict[str, Any]:
        game = ScenarioGame.load(self.scenario_path)
        return {
            "title": game.title,
            "stat_labels": game.stat_labels,
            "characters": game.character_options(),
            "asset_slots": {
                "background": "web/assets/backdrop.svg",
                "portraits": "web/assets/portraits/",
                "music": "web/assets/music/",
            },
        }


class RequestHandler(SimpleHTTPRequestHandler):
    server_version = "InfluencerGameHTTP/1.0"

    def __init__(self, *args: Any, game_server: GameServer, **kwargs: Any) -> None:
        self.game_server = game_server
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/game":
            self.write_json(self.game_server.metadata())
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()

            if parsed.path == "/api/start":
                data = self.game_server.new_session(
                    character_id=str(payload["character_id"]),
                    seed=payload.get("seed"),
                )
                self.write_json(data)
                return

            if parsed.path == "/api/choose":
                session = self.game_server.get_session(str(payload["session_id"]))
                choice_number = payload.get("choice_number")
                if choice_number is not None:
                    choice_number = int(choice_number)
                self.write_json(session.choose(choice_number))
                return

            if parsed.path == "/api/next-day":
                session = self.game_server.get_session(str(payload["session_id"]))
                self.write_json(session.next_day())
                return

            self.write_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except (ScenarioError, KeyError, TypeError, ValueError) as exc:
            self.write_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def find_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 20):
        try:
            httpd = ThreadingHTTPServer((host, port), SimpleHTTPRequestHandler)
        except OSError:
            continue
        httpd.server_close()
        return port
    raise OSError("사용 가능한 포트를 찾지 못했습니다.")


def main(argv: list[str] | None = None) -> int:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run the influencer web game.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    args = parser.parse_args(argv)

    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        print(f"시나리오 파일을 찾을 수 없습니다: {scenario_path}", file=sys.stderr)
        return 1

    port = find_available_port(args.host, args.port)
    game_server = GameServer(scenario_path)
    handler = partial(RequestHandler, game_server=game_server)
    httpd = ThreadingHTTPServer((args.host, port), handler)

    if sys.stdout:
        print(f"웹게임 실행 중: http://{args.host}:{port}")
        print(f"사용 시나리오: {scenario_path}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    boot_log("starting web_game_server.py")
    try:
        exit_code = main()
        boot_log(f"exited with {exit_code}")
        raise SystemExit(exit_code)
    except Exception:
        boot_log(traceback.format_exc())
        raise
