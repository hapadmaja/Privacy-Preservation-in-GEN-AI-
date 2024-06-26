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
df = pd.read_csv("adult_up.txt", sep=", ", header=None, names=names, index_col=False, engine='python');

print(df.head())
print("check if there are missing values")
print(df.isna().sum())
for name in categorical:
    df[name] = df[name].astype('category')

def get_spans(df, partition, scale=None):
    spans = {}
    for column in df.columns:
        if column in categorical:
            span = len(df[column][partition].unique())
        else:
            span = df[column][partition].max()-df[column][partition].min()
        if scale is not None:
            span = span/scale[column]
        spans[column] = span
    return spans
    
full_spans = get_spans(df, df.index)
print(full_spans)

def split(df, partition, column):
    dfp = df[column][partition]
    if column in categorical:
        values = dfp.unique()
        lv = set(values[:len(values)//2])
        rv = set(values[len(values)//2:])
        return dfp.index[dfp.isin(lv)], dfp.index[dfp.isin(rv)]
    else:        
        median = dfp.median()
        dfl = dfp.index[dfp < median]
        dfr = dfp.index[dfp >= median]
        return (dfl, dfr)

def is_k_anonymous(df, partition, sensitive_column, k=5):
    if len(partition) < k:
        return False
    return True

def partition_dataset(df, feature_columns, sensitive_column, scale, is_valid):
    finished_partitions = []
    partitions = [df.index]
    while partitions:
        partition = partitions.pop(0)
        spans = get_spans(df[feature_columns], partition, scale)
        for column, span in sorted(spans.items(), key=lambda x:-x[1]):
            lp, rp = split(df, partition, column)
            if not is_valid(df, lp, sensitive_column) or not is_valid(df, rp, sensitive_column):
                continue
            partitions.extend((lp, rp))
            break
        else:
            finished_partitions.append(partition)
    return finished_partitions

feature_columns = ['age', 'education-num']
sensitive_column = 'income'
finished_partitions = partition_dataset(df, feature_columns, sensitive_column, full_spans, is_k_anonymous)

print(len(finished_partitions))


def build_indexes(df):
    indexes = {}
    for column in categorical:
        values = sorted(df[column].unique())
        indexes[column] = { x : y for x, y in zip(values, range(len(values)))}
    return indexes

def get_coords(df, column, partition, indexes, offset=0.1):
    if column in categorical:
        sv = df[column][partition].sort_values()
        l, r = indexes[column][sv[sv.index[0]]], indexes[column][sv[sv.index[-1]]]+1.0
    else:
        sv = df[column][partition].sort_values()
        next_value = sv[sv.index[-1]]
        larger_values = df[df[column] > next_value][column]
        if len(larger_values) > 0:
            next_value = larger_values.min()
        l = sv[sv.index[0]]
        r = next_value
    l -= offset
    r += offset
    return l, r

def get_partition_rects(df, partitions, column_x, column_y, indexes, offsets=[0.1, 0.1]):
    rects = []
    for partition in partitions:
        xl, xr = get_coords(df, column_x, partition, indexes, offset=offsets[0])
        yl, yr = get_coords(df, column_y, partition, indexes, offset=offsets[1])
        rects.append(((xl, yl),(xr, yr)))
    return rects

def get_bounds(df, column, indexes, offset=1.0):
    if column in categorical:
        return 0-offset, len(indexes[column])+offset
    return df[column].min()-offset, df[column].max()+offset

indexes = build_indexes(df)
column_x, column_y = feature_columns[:2]
rects = get_partition_rects(df, finished_partitions, column_x, column_y, indexes, offsets=[0.0, 0.0])

print(rects[:10])

def plot_rects(df, ax, rects, column_x, column_y, edgecolor='black', facecolor='none'):
    for (xl, yl),(xr, yr) in rects:
        ax.add_patch(patches.Rectangle((xl,yl),xr-xl,yr-yl,linewidth=1,edgecolor=edgecolor,facecolor=facecolor, alpha=0.5))
    ax.set_xlim(*get_bounds(df, column_x, indexes))
    ax.set_ylim(*get_bounds(df, column_y, indexes))
    ax.set_xlabel(column_x)
    ax.set_ylabel(column_y)

pl.figure(figsize=(20,20))
ax = pl.subplot(111)
plot_rects(df, ax, rects, column_x, column_y, facecolor='r')
pl.scatter(df[column_x], df[column_y])
pl.show()

def agg_categorical_column(series):
    return [','.join(set(series))]

def agg_numerical_column(series):
    return [series.mean()]


def build_anonymized_dataset(df, partitions, feature_columns, sensitive_column, max_partitions=None):
    aggregations = {}
    for column in feature_columns:
        #print('agg_categorical _ col : ',agg_categorical_column(df))
        if column in categorical:
         #   print('agg_categorical _ col : ',agg_categorical_column)
            aggregations[column] = agg_categorical_column
        else:
            aggregations[column] = agg_numerical_column
    rows = []
    for i, partition in enumerate(partitions):
       # print("Finished {} partitions...".format(i))
        if i % 100 == 1:
            print("Finished {} partitions...".format(i))
        if max_partitions is not None and i > max_partitions:
            #print('going to break ... ')
            break
       # print('did not break ... ')
        grouped_columns = df.loc[partition].agg(aggregations, squeeze=False)
       # print('finished grouping ')
        sensitive_counts = df.loc[partition].groupby(sensitive_column).agg({sensitive_column : 'count'})
        values = {}
        for name,val in grouped_columns.items():
            values[name] = val[0]
        #values = grouped_columns.iloc[0].to_dict()
        #values = grouped_columns.iloc[0].to_dict()
       # print('finished value computation')
        for sensitive_value, count in sensitive_counts[sensitive_column].items():
            if count == 0:
                continue
           # print('value update')
            values.update({sensitive_column : sensitive_value,
                'count' : count})
            rows.append(values.copy())
            #print('rows appended')
    #print(pd.DataFrame(rows))
    return pd.DataFrame(rows)


def build_final_anonymized_dataset(df, partitions, feature_columns, sensitive_column, max_partitions=None):
    aggregations = {}
    for column in feature_columns:
      #print('agg_categorical _ col : ',agg_categorical_column(df))
      if column in categorical:
       #   print('agg_categorical _ col : ',agg_categorical_column)
          aggregations[column] = agg_categorical_column
      else:
          aggregations[column] = agg_numerical_column
    
    rows = []
    for i, partition_index in enumerate(partitions):
        partition = df.index[partition_index]  # Get the actual partition using the index
        #print("partition is ",partition)
        if i % 100 == 1:
            print("Finished {} partitions...".format(i))
        if max_partitions is not None and i > max_partitions:
            break
        
        grouped_columns = df.loc[partition].agg(aggregations, squeeze=False)
        sensitive_counts = df.loc[partition].groupby(sensitive_column).agg({sensitive_column: 'count'})
        #print( "grouped_columns" , grouped_columns)
        #print("sensitive_counts ", sensitive_counts)
        # trying to access the indexes in partition
        for j in partition:
           #print("Index value is ",j)
            #print("age " ,grouped_columns[0])
            #print("edu num ",grouped_columns[1])
            df.loc[j, 'age'] = grouped_columns[0]
            df.loc[j,'education-num']=grouped_columns[1]
    
    return df

# Example usage:
# anonymized_df = build_anonymized_dataset(original_df, partitions, feature_columns=['age', 'education-num', 'other_column'], sensitive_column='sensitive_attr', max_partitions=None)
mdf=df.copy()
dfn = build_anonymized_dataset(df, finished_partitions, feature_columns, sensitive_column)
print(dfn)
print(dfn.sort_values(feature_columns+[sensitive_column]))
# writing into excel file
dfn.to_csv("anonymised_k.csv")

'''modified_df= build_final_anonymized_dataset(mdf, finished_partitions, feature_columns, sensitive_column)
modified_df.to_csv("k-modified_dataset.csv")'''

# Select quasi-identifiers
qi_columns=feature_columns
# Count distinct combinations of QI attributes
orig_n = df[qi_columns].drop_duplicates().shape[0]  
mondrian_n = dfn[qi_columns].drop_duplicates().shape[0]
print("orig_n : ",orig_n)
print("mondrian_n",mondrian_n)
# Calculate Discernibility Metric
discernibility = orig_n - mondrian_n

print('Discernibility Metric for Mondrian: ', discernibility)


print('sorted')

def diversity(df, partition, column):
    return len(df[column][partition].unique())

def is_l_diverse(df, partition, sensitive_column, l=2):
    return diversity(df, partition, sensitive_column) >= l

finished_l_diverse_partitions = partition_dataset(df, feature_columns, sensitive_column, full_spans, lambda *args: is_k_anonymous(*args) and is_l_diverse(*args))

print(len(finished_l_diverse_partitions))

column_x, column_y = feature_columns[:2]
l_diverse_rects = get_partition_rects(df, finished_l_diverse_partitions, column_x, column_y, indexes, offsets=[0.0, 0.0])

pl.figure(figsize=(20,20))
ax = pl.subplot(111)
plot_rects(df, ax, l_diverse_rects, column_x, column_y, edgecolor='b', facecolor='b')
plot_rects(df, ax, rects, column_x, column_y, facecolor='r')
pl.scatter(df[column_x], df[column_y])
pl.show()

dfl = build_anonymized_dataset(df, finished_l_diverse_partitions, feature_columns, sensitive_column)
dfl.to_csv("anonymised_l.csv")

print(dfl.sort_values([column_x, column_y, sensitive_column]))

global_freqs = {}
total_count = float(len(df))
group_counts = df.groupby(sensitive_column)[sensitive_column].agg('count')
for value, count in group_counts.to_dict().items():
    p = count/total_count
    global_freqs[value] = p

print(global_freqs)

def t_closeness(df, partition, column, global_freqs):
    total_count = float(len(partition))
    d_max = None
    group_counts = df.loc[partition].groupby(column)[column].agg('count')
    for value, count in group_counts.to_dict().items():
        p = count/total_count
        d = abs(p-global_freqs[value])
        if d_max is None or d > d_max:
            d_max = d
    return d_max

def is_t_close(df, partition, sensitive_column, global_freqs, p=0.2):
    if not sensitive_column in categorical:
        raise ValueError("this method only works for categorical values")
    return t_closeness(df, partition, sensitive_column, global_freqs) <= p

finished_t_close_partitions = partition_dataset(df, feature_columns, sensitive_column, full_spans, lambda *args: is_k_anonymous(*args) and is_t_close(*args, global_freqs))

print(len(finished_t_close_partitions))
print("The partitions after the t-closeness applied ")
#print(finished_t_close_partitions)
dft = build_anonymized_dataset(df, finished_t_close_partitions, feature_columns, sensitive_column)

print(dft.sort_values([column_x, column_y, sensitive_column]))
dft.to_csv("anonymised_t.csv")


mdf=df.copy()
modified_df= build_final_anonymized_dataset(mdf, finished_t_close_partitions, feature_columns, sensitive_column)
modified_df.to_csv("t-modified_dataset.csv")

shuffled_df = modified_df.sample(frac=1)  # frac=1 returns all rows (shuffled)
shuffled_df.to_csv("randomised_t-modified_dataset.csv")

column_x, column_y = feature_columns[:2]
t_close_rects = get_partition_rects(df, finished_t_close_partitions, column_x, column_y, indexes, offsets=[0.0, 0.0])

pl.figure(figsize=(20,20))
ax = pl.subplot(111)
plot_rects(df, ax, t_close_rects, column_x, column_y, edgecolor='b', facecolor='b')
pl.scatter(df[column_x], df[column_y])
pl.show()


# Select quasi-identifiers
qi_columns=feature_columns

# Count distinct combinations of QI attributes
orig_n = df[qi_columns].drop_duplicates().shape[0]  
mondrian_n = dft[qi_columns].drop_duplicates().shape[0]
print("orig_n : ",orig_n)
print("mondrian_n",mondrian_n)
# Calculate Discernibility Metric
discernibility = orig_n - mondrian_n

print('Discernibility Metric for Mondrian: ', discernibility)
