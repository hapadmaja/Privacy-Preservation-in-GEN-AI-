# -*- coding: utf-8 -*-
"""
Created on Thu Apr 11 15:16:12 2024

@author: LENOVO
"""

import pandas as pd
import matplotlib.pylab as pl
import matplotlib.patches as patches
names = (
    'age',
    'workclass', 
    'fnlwgt', 
    'education',
    'education-num',
    'marital-status',
    'occupation',
    'relationship',
    'race',
    'sex',
    'capital-gain',
    'capital-loss',
    'hours-per-week',
    'native-country',
    'income',
)

categorical = set((
    'workclass',
    'education',
    'marital-status',
    'occupation',
    'relationship',
    'sex',
    'native-country',
    'race',
    'income',
))
#df = pd.read_csv("./data/k-anonymity/adult.all.txt", sep=", ", header=None, names=names, index_col=False, engine='python');
df = pd.read_csv("adult.all.txt", sep=", ", header=None, names=names, index_col=False, engine='python');

print(df.head())

df['age-group']=pd.cut(df['age'],bins=10)
df['edu-num-group']=pd.cut(df['education-num'],bins=4)
print("After generalising")
print(df.head())

df.to_csv("generalised.csv")
