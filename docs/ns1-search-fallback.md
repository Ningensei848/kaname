# NS1: 検索キーワード・本文のGoogle検索フォールバック

2026-10-12 JST。実装・ローカル検証済み、本番Pagesの受入は進行中です。

## 利用時の挙動

検索キーワードと本文のWikiLinkは、公開manifestに同じタイトルのNoteが一意にあれば内部Noteへ移動します。一致なし・同名複数・公開除外なら、表示語句のGoogle検索を別タブで開きます。検索リンクは↗とアクセシブルなGoogle検索の説明で識別できます。ページ表示・ビルド時のGoogle通信はありません。APIキーや追加LLM呼出しも不要です。

別名表示では検索語に対象名、表示には別名を使います。内部Noteの見出し指定は維持し、Noteが未解決ならNote名だけを検索します。存在しない内部見出しは検索へ隠さず、Webリンク監査が拒否します。コードspan・fence・indented code・エスケープ・URL・Markdownリンク・画像・Wiki埋込みは変換しません。

解決規則は従来どおりタイトル完全一致です。Graph Qualityの正規化/同義語は評価案であり、公開リンクに自動適用しません。同名から任意のNoteを選ぶことや、タイトル部分一致で推定することもありません。

## 新規Noteの本文

既存のrelated_conceptsを候補とし、新規NoteのAI要約・重要ポイント・資料の位置づけに現れる語句を共通composerでWikiLinkにします。長い候補を優先し、ASCII識別子の途中・バージョン名の一部は一致させません。3文字未満、AI/API/data/model等の一般語、概念名の安全な形式に適合しない候補は本文でリンク化しません。安全なMarkdown escapingを維持し、LLMが記述した既存リンク・URL・画像alt・コードには重ねて挿入しません。

保存されたdescriptionとLLM出力は記法を付ける前の文です。要約字数・本文入力上限・出力上限・Batch schemaを変えません。standard/Batchとも同じ組立てと公開検証を使い、画像の配置・receipt/index一致を維持します。

公開Note検証は従来のplain本文と、候補に基づく正確なリンク付き本文だけを認めます。任意の外部Markdownリンク、未宣言のWikiLink、別名の挿入、HTMLを許容する検証緩和は行いません。旧Noteの保存bytes・Note ID・manifest schemaは維持し、本文への自動付与は新規Noteからです。

## 検証・受入

- [x] クエリ符号化・別名/見出し・保護構文・長い候補優先・部分一致拒否・standard/Batch共通保存と公開、未宣言リンク拒否・アンカー監査を40件で検証。
- [x] 関連151件とPython全542件が成功。
- [x] 架空3 Noteの固定QuartzビルドとChromium受入。本文とキーワードの検索リンク18件、内部Note遷移、Google通信を代替するクリック1回、openerなし・4表示幅・画像・元Markdown一致を確認。
- [x] 固定実content125 NoteのChromium受入。検索リンク612件、代替クリック1回・opener不在・4表示幅・承認画像103回・想定外通信0、元bytes/ID/dataset不変を確認。
- [ ] PR/main CIと取込。
- [ ] 本番Pages更新・配信版/元Markdown照合。追加生成0を確認して完了とする。

公開元contentは`b6800161a0f51f07104d1927bf51ead7b7aff4f6`、dataset digestは`53c7ca546d75abfdca08e802c56f79f19d3e9f917c42fc1c7141b010d1a7f9a1`です。Web投影・成果物digestと元dataset digestを区別します。外部検索をNote間のgraph edgeへ数えず、CSPのresource通信許可も広げません。

## 操作範囲と後続

ユーザーから追加Gemini API費用合計USD 1までの承認を受領しました。今回のNS1実装・ローカル受入はGemini呼出し0で進めています。請求明細待ち#116とsource復旧受入待ち#139/#140は独立して追跡し、Web検索導線の完了をこれらの復旧と混同しません。
