import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler

from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dense, Activation, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.models import Model
from tensorflow.keras.layers import GRU, LSTM
from tensorflow.keras.layers import  Input,multiply, Lambda
from sklearn.model_selection import train_test_split

dataset = pd.read_csv('Frequency_ROCOF.csv')
df = np.array(dataset)
df = df[:, :-1]

size0 = df.shape[0]
# l1,l2 is the input to the discriminator
l1 = 20 
l2 = 20
l3 = int(l2/4)

#size of the input variable
noise_dim = 800


scaler_X = MinMaxScaler()
df = scaler_X.fit_transform(df)

df = df.reshape((size0,1,400))
df = df.reshape((size0,100,4)) 
X = np.zeros((size0,l1,l2))


# X is the input to the LSTM-RNN 20 time steps and 20 inputs in eacch time step
for k in range(size0):
    for i in range(l1):
        for j in range(4):
            X[k,i,j*l3:(j+1)*l3] = df[k,i*l3:(i+1)*l3,j]
            
X = X.astype('float32')
X = X[0:8000,:,:]
size0=8000
            
params = {
    "epochs": 100,
    "batch_size": 64,
    "seq_length": 20,
    "dropout_keep_prob": 0.1,
    "hidden_unit": 500,
    "validation_split": 0.1,
    "input_size": 4
}
        


layers = [X.shape[1], X.shape[2], params['hidden_unit'], 1]

def attention_3d_block(inputs,layer_name):
    # inputs.shape = (batch_size, time_steps, input_dim)

    name = layer_name
    input_dim = int(inputs.shape[2])
    a = Permute((2, 1))(inputs)
    a = Reshape((input_dim, TIME_STEPS))(a) # this line is not useful. It's just to know which dimension is what.
    a = Dense(TIME_STEPS, activation='softmax')(a)
    #print(a.shape)
    if SINGLE_ATTENTION_VECTOR:
        a = Lambda(lambda x: K.mean(x, axis=1))(a)
        a = RepeatVector(input_dim)(a)
    a_probs = Permute((2, 1),name=name)(a)
    output_attention_mul = multiply([inputs, a_probs])
    return output_attention_mul


def make_discriminator(layers,params):

    inp = Input(shape=(layers[0], layers[1]))
    inp_att = attention_3d_block(inp,"inp_att")
    layer_1=LSTM(units=layers[2],batch_size= params["batch_size"], return_sequences=True, activation='relu')(inp_att)
    dropout_1=Dropout(params['dropout_keep_prob'])(layer_1)
    layer_2=LSTM(units=layers[2],batch_size= params["batch_size"], return_sequences=True, activation='relu')(dropout_1)
    dropout_2=Dropout(params['dropout_keep_prob'])(layer_2)
    layer_3=LSTM(units=layers[2],batch_size= params["batch_size"], return_sequences=True, activation='relu')(dropout_2)
    dropout_3=Dropout(params['dropout_keep_prob'])(layer_3)
    out_att = attention_3d_block(drop_out3,"out_app")
    fla = Flatten()(out_app)
    dense_1= Dense(units=100)(fla)

    dense_2=Dense(units=layers[3],activation='sigmoid')(dense_1)

    model = Model(inputs=inp, outputs=dense_2)

    return model


# Verify this model with internet/Shahram
def make_generator(layers, params):
    
    inp = Input(shape=(params["seq_length"],noise_dim/params["seq_length"]))

    layer_1=LSTM(units=layers[2],batch_size= params["batch_size"], return_sequences=True, activation='sigmoid')(inp)
    dropout_1=Dropout(params['dropout_keep_prob'])(layer_1)
    
    layer_2=LSTM(units=layers[2],batch_size= params["batch_size"], return_sequences=False, activation='sigmoid')(dropout_1)
    dropout_2=Dropout(params['dropout_keep_prob'])(layer_2)
    
    #layer_3=LSTM(units=layers[0],batch_size= params["batch_size"], return_sequences=True, activation='sigmoid')(dropout_2)
    #dropout_3=Dropout(params['dropout_keep_prob'])(layer_3)
    
    #fla = Flatten()(dropout_1)
    dense_1=Dense(units=l1*l2, activation='sigmoid')(dropout_2)


    model = Model(inputs=inp, outputs=dense_1)

    return model



cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def discriminator_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss
def discriminator_loss1(real_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    total_loss = real_loss 
    return total_loss
def discriminator_loss2(fake_output):
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = fake_loss
    return total_loss

def generator_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output), fake_output)   

generator_optimizer = tf.keras.optimizers.SGD(lr=0.0001)
discriminator_optimizer = tf.keras.optimizers.SGD(lr=0.0001)


generator = make_generator(layers,params)
generator.summary()
discriminator = make_discriminator(layers,params)
discriminator.summary()

@tf.function
def train_step(images):
    noise = tf.random.normal([params["batch_size"], noise_dim])
    # to convert into the input dimensions of tnoise = tf.reshape(noise,[params["batch_size"],params["seq_length"], noise_dim/params["seq_length"]])he generator 
    noise = tf.reshape(noise,[params["batch_size"],params["seq_length"], noise_dim/params["seq_length"]])

    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
      generated_images = generator(noise, training=True)
      generated_images = tf.reshape(generated_images,[params["batch_size"],params["seq_length"],l2])
      real_output = discriminator(images, training=True)
      fake_output = discriminator(generated_images, training=True)
    
      gen_loss = generator_loss(fake_output)
      disc_loss = discriminator_loss(real_output, fake_output)
      
    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))
    
images1 = X[50:114,:,:]
gloss = np.zeros(params["epochs"],)
dloss1 = np.zeros(params["epochs"],)
dloss2 = np.zeros(params["epochs"],)
graph = np.zeros((size0,l1,l2))
draw = np.zeros((100,1))
draw1 = np.zeros((100,1))
draw2 = np.zeros((100,1))
draw3 = np.zeros((100,1))
actual = np.zeros((100,1))
actual[:,0] = df[89,:,0]
actual1 = df[39,:,0]
xaxis = np.arange(0,100,1)
mmdval = np.zeros((100,))
import time
def train(X, epochs):
  for epoch in range(epochs):
      h=time.time()
      print(epoch)
      h=time.time()
      for i in range(133):
          train_step(X[i*64:(i+1)*64,:,:])
      print("inside")
      noise1 = tf.random.normal([size0, int(noise_dim)])
      noise1 = tf.reshape(noise1,[size0,params["seq_length"], int(noise_dim/params["seq_length"])])
      generated_images1 = generator(noise1, training=False)
      generated_images1 = tf.reshape(generated_images1,[size0,l1,l2])
      graph = sess.run(generated_images1)
      for k in range(l1):
          draw[k*l3:(k+1)*l3,0] = graph[89,k,0:5]
          draw1[k*l3:(k+1)*l3,0] = graph[39,k,0:5]
      plt.plot(xaxis,draw,label='fake')
      #plt.plot(xaxis,draw1)
      #plt.plot(xaxis,draw2)
      plt.plot(xaxis,actual,label='true')
      plt.legend()
      plt.ylim(0,1)
      plt.show()
      plt.plot(xaxis,draw1,label='fake')
      plt.plot(xaxis,actual1,label='true')
      plt.legend()
      plt.ylim(0,1)
      plt.show()
      real_output1 = discriminator(images1, training=False)
      fake_output1 = discriminator(generated_images1, training=False)
      gen_loss1 = generator_loss(fake_output1)
      disc_loss1 = discriminator_loss1(real_output1)
      disc_loss2 = discriminator_loss2(fake_output1)
      gloss[epoch]=sess.run(gen_loss1)
      dloss1[epoch]=sess.run(disc_loss1)
      dloss2[epoch]=sess.run(disc_loss2)
      sum=0
      for k in range(size0):
        actual[:,0]=df[k,:,0]
        for r in range(l1):
          draw[r*l3:(r+1)*l3,0] = graph[k,r,0:5]
        sum += poly_mmd2(actual,draw)
      
      mmdval[epoch]=sum/size0
      print(mmdval[epoch])
      print(sess.run(gen_loss1))
      print(sess.run(disc_loss1))
      print(sess.run(disc_loss2))
      print("outside")
      print(time.time()-h)
          

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    train(X,params["epochs"])
    

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    print(sess.run(discriminator_loss2(discriminator.predict(check))))

xx = np.arange(0,20,1)
plt.plot(xx,gloss,label="generator_loss")
plt.plot(xx,dloss1, label="dis_loss_real")
plt.ylim(0,1)
plt.legend()
plt.show()
