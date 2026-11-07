# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：第何回かを指定せず確認問題の出力を頼むとLLMは第1回から3問出力し、エージェントは第何回かの確認をしてきた。
- `--trace` で見えたツール呼び出し（ツール名と引数）：make_quiz({'lecture': 2})
- 1つの質問での LLM 呼び出し回数（`requests`）：2
- 追加したツールと、docstring に書いた説明：def make_quiz(lecture: int) -> str:
    """指定した回の用語から1つを選び、確認問題と答えをJSONで返す。

    問題は用語の定義を示し、用語名を答えてもらう形式。
    「第2回の確認問題を出して」のように、
    復習用の問題を求められたときに使う。
    """
    terms = [term for term in load_glossary() if term["lecture"] == lecture]
    if not terms:
        available = sorted({term["lecture"] for term in load_glossary()})
        return (
            f"第{lecture}回の用語が見つかりません。"
            f"用語集にある回: {', '.join(map(str, available))}"
        )

    term = random.choice(terms)
    return json.dumps(
        {
            "question": f"次の説明に当てはまる用語は何ですか？\n{term['definition']}",
            "answer": term["term"],
        },
        ensure_ascii=False,
    )

## 宿題

- 取り組んだレベル：実装
- やったこと：学習の記録を保存するツール save_learning_log を作った。
- 結果：uv run python -m app.agent "学習記録を保存して。テーマは確認問題を通して、AIE講座第2回を復習したこと。"というコードを実行することで、20261107_053922_549163.jsonを生成し、中身は{
  "topic": "AIE講座第2回復習",
  "note": "確認問題を通して、AIE講座第2回を復習したこと。"
}となった。
また、保存の前に確認を挟む機能も追加した。
--traceの結果は以下の通り。[tool call]   save_learning_log({'topic': 'AIE講座第2回復習', 'note': '確認問題を通して、AIE講座第2回を復習したこと。'})
[tool return] save_learning_log -> 学習記録を保存しました: 20261107_055142_133867.json…
リクエストは1だった。
- 気づき・疑問：記録は確かにされたが、「今日11月7日に私は何をした？」と質問しても行動記録を確認する機能を持っていないとの返事がきた。記録する機能だけでは記録を読みだすことはできないことがわかった。生成AIを使っていると、記録ができれば読み出しも出いるという誤った先入観をもってしまっていた。
