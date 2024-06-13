## GUI Grounding Training Data Processing

```bash
mkdir training_data
cd training_data
```

### Seeclick Web Data

```bash
mkdir seeclick_web
cd seeclick_web
wget "https://box.nju.edu.cn/f/6a804cf190dd490a808f/?dl=1" -O seeclick_web_imgs.zip
wget "https://box.nju.edu.cn/f/3b0f6ccb8bed476c8e39/?dl=1" -O seeclick_web.json
unzip seeclick_web_imgs.zip -x "__MACOSX/*"
mv cpfs01/user/chengkanzhi/seeclick_web_imgs seeclick_web_imgs
cd ..

https://console.cloud.google.com/storage/browser/gresearch/android-in-the-wild/general?pageState=(%22StorageObjectListTable%22:(%22f%22:%22%255B%255D%22))
```

### Download RICO Image Dataset

```bash
wget "https://box.nju.edu.cn/f/7ae5e9bd4bf840d4add3/?dl=1" -O rico_imgs.zip
unzip rico_imgs.zip -x "__MACOSX/*"
wget "https://box.nju.edu.cn/f/4019422e045b480f8945/?dl=1" -O widget_captioning.json
wget "https://box.nju.edu.cn/f/1b54f3b4bf864775b78c/?dl=1" -O ricosca.json
cd ..
```

### Mind2Web/AITW/MoTIF are already downloaded for evaluation


```bash
python finetune/process_data.py --mobile_imgs raw_data/mobile/combined --web_imgs raw_data/seeclick_web/seeclick_web_imgs --widgetcap_json raw_data/mobile/widget_captioning.json --ricosca_json raw_data/mobile/ricosca.json --web_json raw_data/seeclick_web/seeclick_web.json --output_dir evals/datasets/gui_grounding_train
```