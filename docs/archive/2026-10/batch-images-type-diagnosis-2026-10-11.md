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


## 追加枠の提出時拒否とAPI契約に基づく修正

[PR #151](https://github.com/Ningensei848/kaname/pull/151)の[PR CI38137799724](https://github.com/Ningensei848/kaname/actions/runs/38137799724)と[main CI38137906523](https://github.com/Ningensei848/kaname/actions/runs/38137906523)成功後、main b3e64ac1229bb325cb686bf01ca2d1a28c32c2fcから[1件枠38138049639](https://github.com/Ningensei848/kaname/actions/runs/38138049639)を一度だけ起動しました。
[提出前検査38137324307](https://github.com/Ningensei848/kaname/actions/runs/38137324307)はready、監査0・成功335/pending72、未決済/不明usage0でした。

- [x] APIが提出をClientErrorで拒否。台帳complete/submission_rejected、API job名なし。batch_submitted/standard call/保存/復旧0。新しい有料job・Batch usage recordは作られていません。
- [x] [追加提出0の再実行38138656289](https://github.com/Ningensei848/kaname/actions/runs/38138656289)でcollection/audit/cost/Git/Pagesすべてsuccess。Note/receipt/index・拒否台帳と日次/月次費用の不変を確認。通知#152をClose。
- [x] [公式v1beta discovery](https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta)を無料のGETで照合。Schemaの許容fieldにはminProperties/maxPropertiesがあり、additionalPropertiesはありません。固定SDKが送信するadditional_properties falseは、このAPI型定義に適合しません。SDK送信成功だけでAPI受理を保証した検証が不足していました。
- [x] 対策を無料で実装。responseSchemaから非対応additionalPropertiesを除き、全既知キー必須・minProperties=maxPropertiesで閉じたobjectを表現する。親は9キー必須/9個、画像objectは2キー必須/2個。Batchではimagesも必須で、選択なしは[]。他の型/enum/pattern/字数/件数制約と通常standard、保存時のPydantic厳格検証は維持。
- [x] 実SDK送信を公開API field定義のfixtureと照合し、非対応additional_propertiesを含む旧形式がこの検査で拒否される回帰を追加。API提出拒否のHTTP状態/既知field名だけを台帳・inspectへ残す診断も追加。関連78件成功。
- [ ] API契約修正のPR/main CIと、修正後の実Batch成功保存。

今回のClientErrorのHTTP状態・field名は旧台帳に保存されず、API個別の拒否理由は確認できません。API型定義との不適合は確認済みですが、これを保存されていない実APIエラーメッセージの代わりに扱いません。
今回許可された提出操作は終了し、新しい有料提出を止めています。成功保存は未受入です。


## API契約修正後の新しい限定枠

[PR #153](https://github.com/Ningensei848/kaname/pull/153)を[PR CI38138933697](https://github.com/Ningensei848/kaname/actions/runs/38138933697)成功後にmainへ取込み、[main CI38139072690](https://github.com/Ningensei848/kaname/actions/runs/38139072690)も成功しました。API型定義との照合を含む関連78件が成功しています。

前の拒否枠のcostはsuccess・日次/月次推計不変、2026-10月USD 1.09491250です。追加のAPI費用推計は0。追加提出0の収集成功後、拒否台帳・index bytes・Note/receipt世代不変も確認しました。workflow全体のaudit/cost/Git/Pagesも成功し、通知#152をCloseしました。

ユーザーから「この限定枠と受入まで許可する」と別の限定枠を受領しました。
最大1つの生成job/1記事（費用目安約1円）、受付前のschema 400/422拒否のみjob未作成確認後に最大2回の修正再送を許可します。生成結果の不適合・曖昧な提出失敗では再提出しません。適合時の保存/公開・audit/cost・追加生成0の再実行を含みます。
前の拒否枠の後処理完了と状態再確認後に使います。操作枠を別記録にし、課金可能な生成jobは最大1つに制限します。

実APIでの成功保存は、まだ未受入です。


## 新しい限定枠の実行状況

- [x] main 451ff7499f7f132856a5bc5dfd839d6bc0ee4d52のCI成功、既存後処理完了・未決済/不明usage0・保存状態不変を再確認。
- [x] [提出38140244746](https://github.com/Ningensei848/kaname/actions/runs/38140244746)のCollect成功。API生成job 1つ/記事1件を受付、台帳submitted・提出report永続化を照合。受付前のschema拒否は発生せず、修正再送0。
- [ ] 追加生成0の回収と厳格検証、Note/receipt/indexの保存・audit/cost・公開、さらに追加生成0の再実行。

受付済みjobを維持し、提出runの重複する後続公開工程をcancelしました。回収runで監査・費用・公開をまとめて確認します。提出成功を生成結果の適合/保存成功と扱いません。


## 型不適合の解消と残る選択不整合

[回収38140827154](https://github.com/Ningensei848/kaname/actions/runs/38140827154)で、新規jobの結果を追加生成0で回収しました。imagesは必須2キーを持つobject 5件で、JSON schema/Pydanticの型検証に成功しました。以前の文字列配列によるimages:model_typeは解消しました。

ただし、入力の画像候補は4件で、5件の選択は候補外IDか重複IDを必ず含み、selected_imagesの厳格検証で拒否されました。組立てValueError・成功保存0、receipt/成功indexなしです。台帳complete・課金record1・usage欠損0、input 3,514/output 873/thinking 0、費用推計USD 0.00161835（約0.26円）。

- [x] 生成job 1つ/1記事、受付前schema拒否/修正再送0。許可枠を使用済み、生成結果拒否後の有料再提出を停止。
- [x] 次の修正を無料で実装: standard/Batch共通で記事の実候補IDをimage_id.enumに設定し、maxItemsをmin(6, 候補数)に制限。候補0はmaxItems 0で空配列。重複・候補外・存在しない重要ポイントへの配置を引き続き拒否する。
- [x] 候補数/選択数/候補外数/重複数/不存在ポイント数だけの診断を追加し、既存jobのGET検査にも選択検証を適用。ID/本文/値は表示しない。
- [x] 候補制約修正の関連86件成功。実SDK送信で候補0/1/4/12のenum/件数制約を照合し、候補外/重複/不存在ポイントの厳格拒否、4画像保存、GET検査の無書込み、課金record1・再課金0を検証。
- [x] [PR #156](https://github.com/Ningensei848/kaname/pull/156)の[PR CI38141460679](https://github.com/Ningensei848/kaname/actions/runs/38141460679)がPython/Webとも成功、main a0f89a97add180eeee644b5d181d8846843d04cfへ取込み。[main CI38141620406](https://github.com/Ningensei848/kaname/actions/runs/38141620406)も成功。
- [ ] [追加生成0の再実行38141105876](https://github.com/Ningensei848/kaname/actions/runs/38141105876)のaudit/cost/Git/Pagesと課金/保存状態不変の確認。
- [ ] 候補制約修正後の実Batch成功保存。今回の生成結果拒否後は新しい個別承認が必要。

maxItemsとenumは候補外と過剰件数を制限しますが、同じIDの別配置や返却key_points数との不整合までAPIのSchemaでは保証しません。保存時の厳格検証を維持し、不正な返却を変換・削除して成功扱いにしません。


## 候補制約修正後の新しい承認枠

ユーザーから「この追加1件と受入まで許可する」と個別承認を受領しました。最大1生成job/1記事を一度だけ提出し、回収・保存/公開・監査/費用・追加生成0の再実行までを行います。目安約1円、生成結果の再拒否・曖昧な提出失敗では再提出しません。先の後処理完了・既存結果のGET選択診断・main CI成功の確認後に使います。

先の拒否分の費用処理はsuccess、2026-10月USD 1.09653085、未計上/不明/未完了usage0。再実行途中の照合で台帳/課金bytes・index・Note/receipt世代は不変、課金record1です。全工程完了後に改めて照合します。新しい枠は未使用です。
