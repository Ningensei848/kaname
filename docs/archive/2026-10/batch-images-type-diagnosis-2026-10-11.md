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
response_schema経路の未知キー禁止が消えるという以前の判定を訂正します。固定SDKの実送信にはadditional_properties falseがあり、standard/Batch・Pydanticモデル/辞書の4通りすべてで親/画像objectの禁止制約を保持していました。画像文字列を後から変換したり、不正画像を削除して成功扱いにしたりしません。

以前の最大1 job/1 requestの追加枠は使用済みです。今回のGET診断・修正候補作成では有料提出を行いません。
候補のCI成功後、ユーザーから「追加1件と回収・受入を許可する」と新しい最大1 job/1 requestの個別承認を受領しました。提出前検査後に一度だけ試行し、再拒否なら有料再提出を止めます。


## 提出前の送信経路の追加検証

[公式Batch APIのstructured output例](https://ai.google.dev/gemini-api/docs/batch-api)は、inline requestのresponse_schema/responseSchemaを使っています。responseJsonSchemaが非対応であることをこの例だけから断定しません。
有料提出前に、この公式例の経路へBatchのみを合わせます。PR #149の直接画像object定義は維持し、通常standardはresponse_json_schemaを維持します。モデル・prompt・本文・usage/保存処理は維持します。

- [x] 実SDKのresponseSchema送信とstandardのresponseJsonSchemaを比較し、JSON/protobufのフィールド表記、propertyOrdering、default注釈を除いた制約がすべて一致。本文/metadata・他generation設定も一致。
- [x] 親/画像objectの未知キー禁止、画像型・必須キー・ID pattern・配置enum・最大6件を保持すること、文字列3件を厳格拒否して保存0/usage1/再課金0になることを含む関連76件が成功。
- [ ] 送信経路変更のPR/main CIと今回許可された最大1 job/1 requestの実受入。

今回の追加送信経路検証も新規生成0です。許可された新しい1件枠はまだ使用せず、上記検証後に一度だけ使います。
