# 環境設定

## python3導入

```commandline
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
brew install python3
```

上記のコマンドをターミナル上から実行して環境設定

参照: https://qiita.com/7110/items/1aa5968022373e99ae28

## ディレクトリ作成

作業用ディレクトリを作成し、そこに移動する
以下のコマンドは一例

```commandline
mkdir ~/python
cd ~/python
```

## ソースコードのダウンロード

githubからソースコードを取得する

```commandline
git clone https://github.com/threepipes/scraping-open-close.git
cd scraping-open-close
```

参照: https://qiita.com/masamitsu-konya/items/abb572337156e4d003cf


## 仮想環境作成

scraping-open-closeを動作させる環境を構築する

```commandline
python3 -m venv scraping
source scraping/bin/activate
pip install -r requirements.txt
```

参照: 
- https://qiita.com/fiftystorm36/items/b2fd47cf32c7694adc2e
- https://www.lifewithpython.com/2014/03/python-install-multiple-modules-.html

# 動作させる

TODO
