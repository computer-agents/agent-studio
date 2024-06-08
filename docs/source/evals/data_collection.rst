# Data Collection

Though we have provided the processed datasets in an easy-to-use format and recommend to use them directly, here we also record the data downloading and clearning process to make it more transparent and easily reproducible.

```bash

## GUI Gounding

```bash
mkdir raw_data
cd raw_data
```

### Mind2Web

```bash
mkdir mind2web
cd mind2web
wget "https://box.nju.edu.cn/f/33e203d170ab48b0b922/?dl=1" -O mind2web_images.zip
wget "https://box.nju.edu.cn/f/e30b861fa7604668821b/?dl=1" -O mind2web_annots.zip
unzip mind2web_images.zip -x "__MACOSX/*"
unzip mind2web_annots.zip -x "__MACOSX/*"
cd ..
```

### Mobile

```bash
mkdir mobile
cd mobile
```

#### Download RICO Image Dataset

```bash
wget "https://box.nju.edu.cn/f/7ae5e9bd4bf840d4add3/?dl=1" -O rico_imgs.zip
unzip rico_imgs.zip -x "__MACOSX/*"
wget "https://box.nju.edu.cn/f/4019422e045b480f8945/?dl=1" -O widget_captioning.json
wget "https://box.nju.edu.cn/f/1b54f3b4bf864775b78c/?dl=1" -O ricosca.json
cd ..
```

#### Screen Captioning

```bash
mkdir screen_captioning
cd screen_captioning
wget "https://box.nju.edu.cn/f/6bcf4c17ec1b49d2806b/?dl=1" -O screen_captioning.json
cd ..
```

## ScreenSpot

```bash
mkdir screenspot
cd screenspot
wget "https://box.nju.edu.cn/d/5b8892c1901c4dbeb715/files/?p=%2Fscreenspot_desktop.json&dl=1" -O screenspot_desktop.json
wget "https://box.nju.edu.cn/d/5b8892c1901c4dbeb715/files/?p=%2Fscreenspot_imgs.tar&dl=1" -O screenspot_imgs.tar
wget "https://box.nju.edu.cn/d/5b8892c1901c4dbeb715/files/?p=%2Fscreenspot_mobile.json&dl=1" -O screenspot_mobile.json
wget "https://box.nju.edu.cn/d/5b8892c1901c4dbeb715/files/?p=%2Fscreenspot_web.json&dl=1" -O screenspot_web.json
tar --exclude="__MACOSX" -xvf screenspot_imgs.tar
cd ..
```

## AITW

```bash
mkdir aitw
cd aitw
wget "https://box.nju.edu.cn/f/96ba5115bae24eaaa44e/?dl=1" -O aitw_images.zip
wget "https://box.nju.edu.cn/f/1245c74fc09b4565a235/?dl=1" -O aitw_annots.zip
unzip aitw_images.zip -x "__MACOSX/*"
unzip aitw_annots.zip -x "__MACOSX/*"
cd ..
```

## MiniWoB++

```bash
mkdir miniwob
cd miniwob
wget "https://box.nju.edu.cn/f/ac0299ede1e44a93ac77/?dl=1" -O miniwob_images.zip
wget "https://box.nju.edu.cn/f/a84bb9e350e44adf8344/?dl=1" -O miniwob_annots.zip
unzip miniwob_images.zip -x "__MACOSX/*"
unzip miniwob_annots.zip -x "__MACOSX/*"
cd ..
```

## Seeclick Web Data

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


## MoTIF

Download motif_complete.tar.gz from [here](https://drive.google.com/file/d/1_yT0QMUyogA-dS0ozBH8Q9Tn5pH9AdvE/view?usp=share_link)

Download the cleaned json files from [here](https://drive.google.com/file/d/1HD0nuFqAyapxmJiWj8Xhl3LeUDPVRIgm/view)


## Omniact

Download from huggingface. Unzip the `data.zip`. We only use the screenshots in `data/data/{desktop|web}` folder and the annotations in `data/metadata/{desktop|web}/boxes` folder.

```bash
