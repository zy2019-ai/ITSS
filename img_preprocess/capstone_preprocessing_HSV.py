# -*- coding: utf-8 -*-
"""capstone_Preprocessing_Patch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HNT6gDiyKU-K0JAnsYr0xquaTvu4CYfw
"""

from skimage import data
from skimage.color import rgb2hsv
from skimage.color import hsv2rgb
from skimage.exposure import rescale_intensity
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import random
import cv2
import tensorflow as tf
from sklearn.datasets import load_sample_images
from sklearn.feature_extraction import image
import shutil 
from PIL import Image

np.random.seed(42)
tf.random.set_seed(42)

def create_HSV(image_path):
  image_hsv_folder        = "./data/images_aug_hsv/"
  plt.axis('off')

  image_name = os.path.splitext(os.path.basename(image_path))[0]
  print('image_name : ',image_name)
  image_HSV_path  = image_hsv_folder+image_name+'.jpg'
    
  # generate image patch
  if os.path.isfile(image_HSV_path):
    print (image_HSV_path, 'existed , skipping')
  else:
    ihc= cv2.imread(image_path,cv2.IMREAD_COLOR)
    ihc = cv2.cvtColor(ihc,cv2.COLOR_BGR2RGB)
    hsv_img = rgb2hsv(ihc)

    alpha = random.uniform(-1, 1)
    h = hsv_img[:, :, 0] * alpha 
    s = hsv_img[:, :, 1] * alpha
    v =  hsv_img[:, :, 2] 

    hsv_new=np.dstack([h, s,v])
    print('hsv shape : ',hsv_new.shape)

    new_image = hsv2rgb(hsv_new)
    out_img=(new_image * 255).astype(np.uint8)
    im = Image.fromarray(out_img)
    im.save(image_HSV_path)

import os
rootdir = './data/images/'

for subdir, dirs, files in os.walk(rootdir):
    for file in files:
        create_HSV(os.path.join(subdir, file))

