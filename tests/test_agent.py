"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent, run_with_approval

BASE_TOOLS = {"search_glossary", "get_lecture_summary", "save_learning_log"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # 承認が必要なツール（requires_approval=True）は、実行されずに承認待ちになるので戻り値が無い
    waiting = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + waiting == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


def test_save_learning_log_waits_for_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path)
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        pending = agent.run_sync("学習記録を保存してください")

    assert isinstance(pending.output, DeferredToolRequests)
    assert len(pending.output.approvals) == 1
    assert not list(tmp_path.iterdir())

    request = pending.output.approvals[0]
    with agent.override(model=TestModel(call_tools=[])):
        completed = agent.run_sync(
            message_history=pending.all_messages(),
            deferred_tool_results=pending.output.build_results(
                approvals={request.tool_call_id: True}
            ),
        )

    assert completed.output
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_run_with_approval_saves_only_after_user_confirms(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path)
    model = TestModel(call_tools=["save_learning_log"])

    def confirm(prompt):
        assert "保存してよいですか" in prompt
        model.call_tools = []
        return "y"

    monkeypatch.setattr("builtins.input", confirm)
    result = run_with_approval(agent, "学習記録を保存してください", model)

    assert not isinstance(result.output, DeferredToolRequests)
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_run_with_approval_does_not_save_when_user_declines(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", tmp_path)
    model = TestModel(call_tools=["save_learning_log"])

    def decline(prompt):
        assert "保存してよいですか" in prompt
        model.call_tools = []
        return "n"

    monkeypatch.setattr("builtins.input", decline)
    result = run_with_approval(agent, "学習記録を保存してください", model)

    assert not isinstance(result.output, DeferredToolRequests)
    assert not list(tmp_path.iterdir())
