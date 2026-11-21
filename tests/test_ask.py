from types import SimpleNamespace

from app import ask


class FakeChat:
    def __init__(self):
        self.messages = []

    def send_message(self, message):
        self.messages.append(message)
        return SimpleNamespace(
            text="answer",
            usage_metadata=SimpleNamespace(
                prompt_token_count=12,
                candidates_token_count=4,
            ),
        )


class FakeChats:
    def __init__(self):
        self.chat = FakeChat()
        self.models = []

    def create(self, *, model):
        self.models.append(model)
        return self.chat


class FakeClient:
    def __init__(self, *, api_key):
        self.chats = FakeChats()


def test_ask_prints_input_and_output_token_counts(monkeypatch, capsys):
    chat = FakeChat()

    assert ask.ask(chat, "question") == "answer"

    assert capsys.readouterr().out == "[トークン数] 入力: 12, 出力: 4\n"


def test_main_reuses_chat_for_follow_up_questions(monkeypatch):
    client = FakeClient(api_key="test-key")
    monkeypatch.setattr(ask.genai, "Client", lambda **kwargs: client)
    monkeypatch.setattr(ask, "get_api_key", lambda: "test-key")
    monkeypatch.setattr("sys.argv", ["app.ask", "first question"])
    answers = iter(["follow-up question", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    ask.main()

    assert client.chats.models == [ask.MODEL]
    assert client.chats.chat.messages == ["first question", "follow-up question"]