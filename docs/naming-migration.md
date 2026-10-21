# kanameへの名称統一

Issue [#206](https://github.com/Ningensei848/kaname/issues/206)により、Python distribution/import/CLIは`kaname`です。ソースは `src/kaname/`、実行は `python -m kaname` または `kaname` を使います。旧名のCLI/module aliasは提供せず、手元の呼出し元も更新します。

```bash
python -m pip install --no-deps -e .
# 旧distributionを導入していた環境だけ。依存パッケージは削除しません。
python -m pip uninstall techkb
python -m kaname validate-config
kaname --help
```

環境変数は `KANAME_GCS_READ_WORKERS` と `KANAME_READ_CACHE` へ変更します。移行用に旧 `TECHKB_` prefixも読めます。新旧両方がある場合は新名を優先し、新名が不正でも旧値へ黙って戻しません。GCS bucket名・object path・index/receipt/usage/billing ID・公開Note ID/bytes・manifest形式は改名しません。

新しい直接同期先は `kaname/notes/`、管理ファイルは `kaname/.kaname-sync.json`、lockは `.kaname-sync.lock` です。既存の `TechKB/` だけが存在するVaultでは、そのディレクトリ・旧管理ファイル・旧lockを使い続け、人の編集と更新候補を保持します。新旧両ディレクトリが存在する場合は、書込み前に停止します。Vaultを自動で移動・統合しません。利用者がフォルダを移す場合は編集アプリと全syncを止め、編集/候補/管理ファイルを保全してから、フォルダと管理ファイルの名前を一緒に変更してください。稼働中のlockを削除しません。

新しいBatchのdisplay nameと通知markerにはkanameを使います。既存Batchは台帳に保存した旧display nameで照合し、自動再提出しません。通知は閉じたIssueを含む新旧markerを照合し、改名だけで同じ障害を再通知しません。

Actionsのworkflow表示とwriter concurrencyはkanameへ統一します。本番へ反映する際は旧workflowのwriterが終了したことを確認してから新名のworkflowを実行し、新旧concurrency groupのwriterを重ねません。WIFのrepository ID・workflow path・main条件は変更しません。

archive、過去のcommit/blob URL、既存の公開snapshot、外部依存の名称は歴史の証拠として保持します。旧名の文字列は、これらと互換読取りの定数・回帰テストだけに限定します。
