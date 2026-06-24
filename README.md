# 宅建 直前ブースター（Streamlit版）

スマホでもブラウザで開ける、宅建試験の直前対策アプリです。  
**全問4択**、オリジナル問題＋解説つきで、短時間復習と本番形式演習に対応しています。

## できること

- 分野別の4択演習（短時間復習）
- 本番形式50問（構成比: 権利14 / 業法20 / 法令8 / 税その他8）
- 採点、分野別正答率、誤答解説
- 合格推定ライン（過去合格点ベースの独自算出）
- 結果CSVダウンロード
- 購入者向けアクセスキー認証（任意）

## 注意

- 本アプリの問題文・解説は、過去問傾向を踏まえて作成した**オリジナル**です。
- 公式問題文の転載ではありません。
- 法改正があり得るため、最終確認は必ず最新の法令・公式情報で行ってください。

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
