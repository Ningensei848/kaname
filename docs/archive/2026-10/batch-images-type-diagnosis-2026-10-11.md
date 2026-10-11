# #94: images型不適合の切分け（2026-10-11）

現在はP2のBatch成功保存を妨げるimages型不適合に集中しています。

- [x] [PR #148](https://github.com/Ningensei848/kaname/pull/148)で値・未知field名を出さないJSON型診断を追加。関連31件と[PR CI](https://github.com/Ningensei848/kaname/actions/runs/38136804828)成功後、mainへ取込み。
- [x] [GET診断38136914594](https://github.com/Ningensei848/kaname/actions/runs/38136914594)で既存の失敗jobを読取り。新規生成・提出・GCS保存0。APIはSUCCEEDED/STOP、imagesは配列、要素3個すべてstring。期待するImageSelection objectではないため、厳格検証はimages:model_typeのまま拒否。
- [x] 修正候補としてresponseJsonSchemaのimages.itemsにImageSelectionの定義を直接展開。追加property禁止・image_id pattern・after enum・必須2キー・最大6件を維持。本文prompt・model・出力上限・Pydantic厳格受入は維持する。
- [x] [PR #149](https://github.com/Ningensei848/kaname/pull/149)の関連76件・[PR CI38137101692](https://github.com/Ningensei848/kaname/actions/runs/38137101692)成功。main `a0358bc06f2cad2959d20a9c7ba5766652248f23`へ取込み。実SDK送信の制約維持/standard・Batch一致、文字列3件の拒否・保存0・usage回収1・再実行の追加課金0、画像付き保存/公開bytesの回帰を確認。
- [ ] 修正候補の実API受入、適合Note/receipt/index保存、audit/cost/公開bytes、追加提出0の再実行。

## 判明した事実と仮説

型不適合の直接原因は、画像のオブジェクト配列を要求したところ文字列配列が返ったことです。
API内部でこの逸脱が発生する理由は未確定です。既存SDK実HTTP検証ではstandard/Batchは同じpayloadを送り、images.itemsは$defs/ImageSelectionの参照でした。
今回の修正候補は、この入れ子の参照解決への依存をなくします。参照先の定義をそのまま展開するため、schemaの受理するデータ集合は変えません。
参照展開でAPI逸脱が解消するかは実試行前の仮説であり、コード/fixtureテストの成功を実Batch成功保存と扱いません。

[Googleのstructured output説明](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)ではarrayのitems、objectのproperties/required/additionalPropertiesがサポート対象です。最終出力はアプリ側でも検証するよう案内されています。
response_schema経路は固定SDKでadditionalProperties falseが消えたため、今回の候補はresponse_json_schemaを維持します。画像文字列を後から変換したり、不正画像を削除して成功扱いにしたりしません。

以前の最大1 job/1 requestの追加枠は使用済みです。今回のGET診断・修正候補作成では有料提出を行いません。
新たな実試行は、候補のCI成功と具体的な操作範囲の確認後に限定して行います。
