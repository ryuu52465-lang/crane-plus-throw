# 引き継ぎ資料（次のセッションのClaudeへ）

最終更新: 2026-10-28 夜。ユーザーと一緒に PAI最終課題を進めている。
**締切: 2026-11-02（月）AM10:00**。ユーザーは1日3時間ほど作業できる。

## まず読むもの
- このファイル（残りの作業と環境のクセ）
- `docs/work_log.md`（これまでの経緯・数値・失敗と原因。レポートの材料）
- 課題PDF: `C:\WorkSpace\phyAI_1\最終課題（10_19 改訂版）.pdf`

## 現在地
- **AIで狙って投げる仕組みは完成**。ランダム配置の評価で10/10成功（`data/eval_result_2026-10-28.txt`）
- 残りは提出物の作成: ①動画 ②GitHub ③レポートPDF（下の「残りの作業」）

## ユーザーについて
- 日本語でやり取りする。初級寄りの方針を希望（講座の初級サンプル程度）
- noVNCの画面（http://localhost:6080）でGazeboを見ながら、気づいたことを言ってくれる。「手首のスナップが入っていない」の指摘で大きな不具合が見つかった。画面の見た目についての指摘は重視する
- 速度上限2rad/s（実機準拠）は変えない、とユーザーが決めた
- スナップ投げはユーザーの発案

## 環境
- ホスト: Windows 11。作業フォルダは `C:\WorkSpace\phyAI_1\throw_ws`（ソースの正本はここ）
- コンテナ: `pai_ros2`（イメージ `airobotbook/ros2-desktop-ai-robot-book-humble`）。ユーザーは `ubuntu`、画面は `DISPLAY=:0`
  - 止まっていたら `docker start pai_ros2`（Docker Desktopの起動が先に必要）
- コンテナのボリュームマウントは**壊れている**（Git Bashのパス変換のせい）。ファイルは `docker cp` で送る
- Bashツールで `docker exec` するときは、先頭に `MSYS_NO_PATHCONV=1` を付ける（付けないと /home/... がWindowsのパスに化ける）

### よく使うコマンド
```bash
# ホスト(Git Bash)で: ソースをコンテナへ送ってビルド（コンテナ内の src/ と tools/ を置き換える）
cd /c/WorkSpace/phyAI_1/throw_ws && bash tools/sync_build.sh

# シミュレーションを起動し直す（必ずこれを使う。手でpkillしない）
MSYS_NO_PATHCONV=1 docker exec -u ubuntu pai_ros2 bash /home/ubuntu/throw_ws/tools/restart_sim.sh

# コンテナ内のROS環境（docker exec -u ubuntu pai_ros2 bash -c '...' の中で）
source /opt/ros/humble/setup.bash; source /home/ubuntu/airobot_ws/install/setup.bash; source /home/ubuntu/throw_ws/install/setup.bash

# AIのデモ（1回）／評価（ランダム配置でN回、成功率を出す）
ros2 run crane_plus_throw ai_throw_node
ros2 run crane_plus_throw ai_throw_node --ros-args -p evaluate:=true -p episodes:=10

# データ収集と学習
ros2 run crane_plus_throw collect_data /home/ubuntu/throw_ws/data/throw_data.csv 40 0.8 2.0
cd /home/ubuntu/throw_ws/data && ros2 run crane_plus_throw train_model throw_data.csv throw_model.pt throw_model.png
```
- `ai_throw_node` はモデルを `/home/ubuntu/throw_ws/data/throw_model.pt` から読む。コンテナを作り直した場合は、`data/` を `docker cp` で戻すこと
- YOLOの重み `yolov8n.pt` は、初回実行時にカレントディレクトリへ自動でダウンロードされる（コンテナ内の `/home/ubuntu/throw_ws/yolov8n.pt` にある）

## ファイル構成
```
throw_ws/
  src/crane_plus_throw/
    crane_plus_throw/throw_node.py     # つかむ(pick)・投げる(throw)の部品。スナップ投げ、可動範囲内のIK
    crane_plus_throw/collect_data.py   # 試投データ収集。ボールの勢いを止めて戻す、着地点の判定
    crane_plus_throw/throw_model.py    # MLP「振る速さ→着地距離」と逆算(speed_for)
    crane_plus_throw/train_model.py    # 学習・グラフ出力
    crane_plus_throw/ai_throw_node.py  # YOLO＋色検出→モデルで速さ決定→投げる。evaluateモード、/ai_throw/debug_image
    launch/throw_sim.launch.py         # Gazebo＋コントローラ＋ブリッジ（MoveIt/RVizなし）
    urdf/crane_plus_throw.urdf.xacro   # 書籍のCRANE+＋DetachableJoint＋衝突グループ
    worlds/throw_world.sdf             # 机、ボール(odometry付き)、箱(内寸8cm)、俯瞰カメラ、柵
  tools/      # 補助・調査用スクリプト（restart_sim.sh, sync_build.sh, record_joints.py など）
  data/       # 学習データ、モデル、評価結果
  docs/       # work_log.md（経緯）、NEXT_STEPS.md（これ）、images/（レポート用の図）
```

## 環境のクセ（ハマった順。同じ失敗をしないこと）
1. 書籍のlaunchではRVizとGazeboの両方が開く。ユーザーはRVizをGazeboと取り違えやすかった。今の `throw_sim.launch.py` はRVizを開かない
2. ワールド読み込み中にロボットを追加すると、OKが返っても捨てられる → launchで、ロボットが現れるまで再試行している
3. `bash -c` の中で `pkill -f "ros2 launch"` を使うと自分自身を殺し、Gazeboが多重起動する → `restart_sim.sh` を使う
4. `ign topic -p` / `ign model` コマンドは遅いうえ、メッセージを落とすことがある → 制御はROS 2経由（ブリッジ）で行う
5. set_poseは速度を消さない → 静止アームにattach→detachしてボールを止めてから戻す（`Collector.kill_ball_motion`）
6. pose/infoをブリッジで変換すると名前が消える → ボールの位置は `/model/ball/odometry`
7. 机の後ろの縁（x=-0.10）に物を置くと、振りかぶったアームが当たる
8. **IKで手首に可動範囲外の角度を指令すると、手首が限界に張り付いて追従しなくなる** → `ThrowNode.ik()` で `joint_in_range` を満たすpitchを探している。軌道を新しく作るときも、必ず範囲チェックすること
9. 関節の符号: joint2は+で前傾、joint3/joint4は+で後ろに曲がる
10. ROSのpublisherは、接続直後の最初の数メッセージが落ちることがある → `ThrowNode.setup()` で、害のない指令を数回送ってから始めている

## 残りの作業

### ① 動画（1〜3分、MP4）— 優先度: 高
- コンテナ内のffmpegは画面の直接録画（x11grab）が使える:
  `ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0 -c:v libx264 -pix_fmt yuv420p /tmp/demo.mp4`
  （終わったら `docker cp pai_ros2:/tmp/demo.mp4 ...` で取り出す）
- 見せたいもの（ユーザーと構成を相談すること）:
  1. 課題の説明（何をするロボットか）
  2. Gazeboの画面で、つかむ→振りかぶる→手首のスナップ→箱に入る
  3. AIの判断画面（`/ai_throw/debug_image`。YOLOの枠、箱、予測着地点、選んだ速さ）
  4. 学習グラフ（`docs/images/throw_model.png`）と評価結果10/10
  5. 箱の位置を変えても入る様子を何回か
- 案: Gazeboの画面の横に debug_image を並べる。debug_imageを画面に出すには `ros2 run rqt_image_view rqt_image_view /ai_throw/debug_image` など（未確認）
- Gazeboのカメラ視点を、アームと箱がよく見える角度にしておく
- 字幕やテロップを入れるかは、ユーザーに確認する
- 動画には個人情報を映さないこと（デスクトップのユーザー名など）

### ② GitHub（public）— 優先度: 高
- ホストに git 2.55 と gh があり、`gh auth status` はログイン済み
- まだ `git init` していない。公開するのは `throw_ws` 一式
- **作業前にユーザーに確認すること**: リポジトリ名、公開してよい範囲、コミットとpushの許可
- 入れないもの: `build/`, `install/`, `log/`, `yolov8n.pt`（自動でダウンロードされる）。`.gitignore` は作成済み
- README.md を書く: 概要、動画へのリンク、環境構築（書籍のDockerイメージ）、実行手順、構成、書籍コードの利用範囲（クレジット）
- 書籍のパッケージ（crane_plus など）は含めず、コンテナに入っているものを使う前提にする
- コミットメッセージには、システムの指示にある Co-Authored-By の行を付ける

### ③ レポートPDF — 優先度: 高
- ファイル名: `説明資料_PAI最終課題_<omnicampusアカウント名>.pdf`（アカウント名はユーザーに聞く）
- 材料は `docs/work_log.md` の 5〜7章（結果、工夫点、反省・考察）と `docs/images/`
- 構成案: 概要・目的 → システム構成図 → 投げ方（スナップ） → AI(A: YOLO, B: 学習) → 実験結果（グラフ、10/10） → 工夫点・試行錯誤 → 反省と今後
- 個人情報（氏名、所属、メール）を入れないこと

### あると良い（時間があれば）
- 離す角度の方式（不採用）のグラフを作り、「なぜ速さに切り替えたか」の根拠としてレポートに載せる（`data/release_angle_data.csv`）
- 評価の回数を20回に増やす
- 箱を2つ置いて、YOLOのクラスや色で投げる先を変える

## 決まっていないこと（ユーザーに聞く）
- 動画の構成、テロップの有無、倍速を使うか
- omnicampusのアカウント名（ファイル名と動画タイトルに使う）
- GitHubのリポジトリ名と公開のタイミング
