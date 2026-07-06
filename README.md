# 宅建 直前ブースター（Streamlit版）

スマホでもブラウザで開ける、宅建試験の直前対策アプリです。  
**全問4択**、短時間復習と本番形式演習に対応しています。

## できること

- 分野別の4択演習（短時間復習）
- 本番形式50問（構成比: 権利14 / 業法20 / 法令8 / 税その他8）
- 解答スタイル切替（復習モード / 実践モード）
- 採点、分野別正答率、誤答解説
- 合格推定ライン（過去合格点ベースの独自算出）
- 結果CSVダウンロード
- 購入者向けアクセスキー認証（任意）

## 注意

- デフォルトでは、過去問傾向を踏まえて作成した**オリジナル問題**を使用します。
- `data/user_question_bank.json` または `data/user_question_bank.csv` を置くと、
  そのデータを優先して読み込みます（自分用問題データ差し替え）。
- 法改正があり得るため、最終確認は必ず最新の法令・公式情報で行ってください。

## 自分用の問題データを使う

`data/user_question_bank.json` か `data/user_question_bank.csv` を作成すると、
内蔵問題ではなくそのデータを読み込みます。

- テンプレート: `data/user_question_bank_template.csv`
- CSVカラム:
  `id,field,year,difficulty,question,choice1,choice2,choice3,choice4,answer,explanation`
- `answer` は 0〜3（`choice1` が 0）

※ ここに入れた問題データの権利処理は利用者責任です。第三者配布・販売は権利条件を確認してください。

## ローカル実行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 購入者向けアクセスキー（任意）

アクセス制限したい場合は、以下を設定します。

### ローカル

```bash
set ACCESS_KEY=your-secret-key
streamlit run app.py
```

### Streamlit Community Cloud

1. App settings → `Secrets`
2. 次を登録

```toml
ACCESS_KEY = "your-secret-key"
```

設定後、利用者はキー入力しないとアプリに入れません。

## GitHub × Streamlit Community Cloud 公開手順

1. この `takken_streamlit_app` フォルダを GitHub リポジトリに push
2. Streamlit Community Cloud で GitHub 連携
3. `Main file path` を `app.py` に設定してデプロイ
4. 必要なら `Secrets` に `ACCESS_KEY` を登録
5. 発行された URL をココナラ購入者へ案内

## ココナラ販売向けの運用ヒント

- 価格500円帯なら「直前2週間の弱点潰し」に絞った訴求が有効
- 商品ページに「スマホで3分演習」「4択のみ」「誤答解説つき」を明記
- 購入者ごとにキーを変える運用も可能（手動）
