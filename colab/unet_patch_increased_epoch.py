# -*- coding: utf-8 -*-
"""Unet_Patch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1c8PLTmHPihrAK7ElWpbtNdst0yU5To8U
"""

import os
#os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import numpy as np
import cv2
from glob import glob
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from tensorflow.keras.layers import Conv2D, Activation, BatchNormalization
from tensorflow.keras.layers import UpSampling2D, Input, Concatenate
from tensorflow.keras.models import Model
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau,ModelCheckpoint,CSVLogger
from tensorflow.keras.metrics import Recall, Precision
from tensorflow.keras import backend as K
import shutil 
from PIL import Image

print("Tensorflow version: ", tf.__version__)
print(tf.test.gpu_device_name())


# Change working directory to be current folder, please keep ''/content/gdrive/My Drive/XXX' in the path and change XXX to be your own folder.
# The path is case sensitive.

os.chdir('C:/Users/User/Desktop/nus/capstone/NUS_ISS_CAPSTONE/')

# set the randomness and make the results reproducible
np.random.seed(42)
tf.random.set_seed(42)

#hyperparameters 

IMAGE_SIZE = 256
EPOCHS = 36
BATCH = 32
LR = 1e-4
PATH = "CVC-612/"

#This function loads the images and masks, split them into training, validation and testing dataset

def load_data(path, split=0.1):
    train_x = sorted(glob(os.path.join(path, "./img_preprocess/data/images_patch/ZT*")))
    train_y = sorted(glob(os.path.join(path, "./img_preprocess/data/masks_patch/mask_ZT*")))
    
    valid_x = sorted(glob(os.path.join(path, "./img_preprocess/data/validation/*")))
    valid_y = sorted(glob(os.path.join(path, "./img_preprocess/data/masks_val/*")))

    test_x  = sorted(glob(os.path.join(path, "./img_preprocess/data/test/*")))
    test_y  = sorted(glob(os.path.join(path, "./img_preprocess/data/masks_test/*"))) 

    print('train_x :',len(train_x), 'train_y : ',len(train_y))
    print('valid_x : ', len(valid_x), 'valid_y : ',len(valid_y))
    print('test_x : ', len(test_x), 'test_y : ',len(test_y))

    #total_size = len(images)
    #valid_size = int(split * total_size)
    #test_size = int(split * total_size)

    #train_x, valid_x = train_test_split(images, test_size=valid_size, random_state=42)
    #train_y, valid_y = train_test_split(masks, test_size=valid_size, random_state=42)

    #train_x, test_x = train_test_split(train_x, test_size=test_size, random_state=42)
    #train_y, test_y = train_test_split(train_y, test_size=test_size, random_state=42)

    return (train_x, train_y), (valid_x, valid_y), (test_x, test_y)

# read the image and mask , resize ,normalize and return RGB image and a grayscale

def read_image(path):
    path = path.decode()
    x = cv2.imread(path, cv2.IMREAD_COLOR)
    x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
    x = cv2.resize(x, (IMAGE_SIZE, IMAGE_SIZE))
    x = x/255.0
    return x

def read_mask(path):
    path = path.decode()
    x = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    x = cv2.resize(x, (IMAGE_SIZE, IMAGE_SIZE))
    x = x/255.0
    x = np.expand_dims(x, axis=-1)
    return x

#input dataset pipelines

def tf_parse(x, y):
    def _parse(x, y):
        x = read_image(x)
        y = read_mask(y)
        return x, y

    x, y = tf.numpy_function(_parse, [x, y], [tf.float64, tf.float64])
    x.set_shape([IMAGE_SIZE, IMAGE_SIZE, 3])
    y.set_shape([IMAGE_SIZE, IMAGE_SIZE, 1])
    return x, y

def tf_dataset(x, y, batch=8):
    dataset = tf.data.Dataset.from_tensor_slices((x, y))
    dataset = dataset.map(tf_parse)
    dataset = dataset.batch(batch)
    dataset = dataset.repeat()
    return dataset

#convert to the RGB formart
def read_and_rgb(x):
    x = cv2.imread(x)
    x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
    return x

(train_x, train_y), (valid_x, valid_y), (test_x, test_y)= load_data('')

def model():
    inputs = Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3), name="input_image")
    
    encoder = MobileNetV2(input_tensor=inputs, weights="imagenet", include_top=False, alpha=0.35)
    skip_connection_names = ["input_image", "block_1_expand_relu", "block_3_expand_relu", "block_6_expand_relu"]
    encoder_output = encoder.get_layer("block_13_expand_relu").output
    
    f = [16, 32, 48, 64]
    x = encoder_output
    for i in range(1, len(skip_connection_names)+1, 1):
        x_skip = encoder.get_layer(skip_connection_names[-i]).output
        x = UpSampling2D((2, 2))(x)
        x = Concatenate()([x, x_skip])
        
        x = Conv2D(f[-i], (3, 3), padding="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)
        
        x = Conv2D(f[-i], (3, 3), padding="same")(x)
        x = BatchNormalization()(x)
        x = Activation("relu")(x)
        
    x = Conv2D(1, (1, 1), padding="same")(x)
    x = Activation("sigmoid")(x)
    
    model = Model(inputs, x)
    return model

# dice coefficient loss
smooth = 1e-15
def dice_coef(y_true, y_pred):
    y_true = tf.keras.layers.Flatten()(y_true)
    y_pred = tf.keras.layers.Flatten()(y_pred)
    intersection = tf.reduce_sum(y_true * y_pred)
    return (2. * intersection + smooth) / (tf.reduce_sum(y_true) + tf.reduce_sum(y_pred) + smooth)

def dice_loss(y_true, y_pred):
    return 1.0 - dice_coef(y_true, y_pred)

#build input dataset

train_dataset = tf_dataset(train_x, train_y, batch=BATCH)
valid_dataset = tf_dataset(valid_x, valid_y, batch=BATCH)

#compile model

model = model()
model.summary()

modelname= 'Unet_Patch_Increased_Epoch'
folderpath      = './colab/'
filepath        = folderpath + modelname + ".hdf5"
checkpoint      = ModelCheckpoint(filepath, 
                                  monitor='val_accuracy', 
                                  verbose=0, 
                                  save_best_only=True, 
                                  mode='max')

csv_logger      = CSVLogger(folderpath+modelname +'.csv')                       # Step 2
callbacks_list  = []                                       # Step 3

print("Path to model:", filepath)
print("Path to log:  ", folderpath+modelname+'.csv')

# Reduce learning rate or Stop training

callbacks = [
    ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=4),
    EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=False),
    checkpoint,
    csv_logger
]

#define the number of batches in an epoch

train_steps = len(train_x)//BATCH
valid_steps = len(valid_x)//BATCH

if len(train_x) % BATCH != 0:
    train_steps += 1
if len(valid_x) % BATCH != 0:
    valid_steps += 1

opt = tf.keras.optimizers.SGD(lr=1e-4,momentum=0.9,decay=1e-4/25)
metrics = [dice_coef, Recall(), 'accuracy']
model.compile(loss=dice_loss, optimizer=opt, metrics=metrics)

#train the model
model.fit(
    train_dataset,
    validation_data=valid_dataset,
    epochs=EPOCHS,
    steps_per_epoch=train_steps,
    validation_steps=valid_steps,
    callbacks=callbacks
)

#evaluating the trained model on the test dataset
modelGo     = model()   # This is used for final testing
modelGo.load_weights(filepath)

opt = tf.keras.optimizers.SGD(lr=1e-4,momentum=0.9,decay=1e-4/25)
metrics = [dice_coef, Recall(), Precision()]
modelGo.compile(loss=dice_loss, optimizer=opt, metrics=metrics)


test_dataset = tf_dataset(test_x, test_y, batch=BATCH)

test_steps = (len(test_x)//BATCH)
if len(test_x) % BATCH != 0:
    test_steps += 1

modelGo.evaluate(test_dataset, steps=test_steps)

def read_image(path):
    x = cv2.imread(path, cv2.IMREAD_COLOR)
    x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
    x = cv2.resize(x, (IMAGE_SIZE, IMAGE_SIZE))
    x = x/255.0
    return x

def read_mask(path):
    x = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    x = cv2.resize(x, (IMAGE_SIZE, IMAGE_SIZE))
    x = np.expand_dims(x, axis=-1)
    x = x/255.0
    return x

def mask_parse(mask):
    mask = np.squeeze(mask)
    mask = [mask, mask, mask]
    mask = np.transpose(mask, (1, 2, 0))
    return mask

#print result

unet_patch_out_folder='./colab/unet_patch_out/'
for i, (x, y) in enumerate(zip(test_x[:10], test_y[:10])):
    x = read_image(x)
    y = read_mask(y)
    #y_pred = modelGo.predict(np.expand_dims(x, axis=0))[0] > 0.5
    y_pred = modelGo.predict(np.expand_dims(x, axis=0))[0]
    h, w, _ = x.shape
    white_line = np.ones((h, 10, 3))

    all_images = [
        x, white_line,
        mask_parse(y), white_line,
        mask_parse(y_pred)
    ]
    new_image = np.concatenate(all_images, axis=1)
    out_img=(new_image * 255).astype(np.uint8)
    im = Image.fromarray(out_img)
    unet_patch_out_path=unet_patch_out_folder+i+'.jpg'
    im.save(unet_patch_out_path)