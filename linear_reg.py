import numpy as np
import pandas as pd
import xlrd
from tqdm import tqdm
from sklearn.linear_model import LinearRegression, Ridge
from sklearn import preprocessing, cross_validation
from main import find_min_alpha
import matplotlib.pyplot as plt

#### calculate miss values
def col_miss(train_df):
    col_missing_df = train_df.isnull().sum(axis=0).reset_index()
    col_missing_df.columns = ['col', 'missing_count']
    col_missing_df = col_missing_df.sort_values(by='missing_count')
    return col_missing_df


#### obtain cols of XX type
def obtain_x(train_df, xtype):
    dtype_df = train_df.dtypes.reset_index()
    dtype_df.columns = ['col', 'type']
    return dtype_df[dtype_df.type == xtype].col.values


def date_cols(train_df, float_col):
    float_date_col = []
    for col in float_col:
        if train_df[col].min() > 1e13:
            float_date_col.append(col)
    return float_date_col


def float_uniq(float_df, float_col):
    float_uniq_col = []
    for col in tqdm(float_col):
        uniq = float_df[col].unique()
        if len(uniq) == 1:
            float_uniq_col.append(col)
    return float_uniq_col


def cal_corrcoef(float_df, y_train, float_col):
    corr_values = []
    for col in float_col:
        corr_values.append(abs(np.corrcoef(float_df[col].values, y_train) \
                                   [0, 1]))
    corr_df = pd.DataFrame({'col': float_col, 'corr_value': corr_values})
    corr_df = corr_df.sort_values(by='corr_value', ascending=False)
    return corr_df


def build_model(x_train, y_train):
    reg_model = LinearRegression()
    reg_model.fit(x_train, y_train)
    return reg_model

def create_model(x_train, y_train, alpha):
    print("begin to train...")
    model = Ridge(alpha=alpha)
    model.fit(x_train, y_train)
    return model


if __name__ == '__main__':
    # read train data
    print('read train...')
    train_df = pd.read_excel('train.xlsx')
    print('train shape:', train_df.shape)
    # calculate the number of miss values
    col_missing_df = col_miss(train_df)
    # del cols of all nan
    all_nan_columns = col_missing_df[col_missing_df.missing_count == 499]. \
        col.values
    print('number of all nan col:', len(all_nan_columns))
    train_df.drop(all_nan_columns, axis=1, inplace=True)
    print('deleted,and train shape:', train_df.shape)
    # obtain float cols
    float64_col = obtain_x(train_df, 'float64')
    print('obtained float cols, and count:', len(float64_col))
    # del cols that miss number greater than 200
    miss_float = train_df[float64_col].isnull().sum(axis=0).reset_index()
    miss_float.columns = ['col', 'count']
    miss_float_almost = miss_float[miss_float['count'] > 200].col.values
    float64_col = float64_col.tolist()
    float64_col = [col for col in float64_col if col not in \
                   miss_float_almost]
    print('deleted cols that miss number > 200')
    # del date cols
    float64_date_col = date_cols(train_df, float64_col)
    float64_col = [col for col in float64_col if col not in \
                   float64_date_col]
    print('deleted date cols, and number of float cols:', len(float64_col))
    # fill nan
    print('get float cols data and fill nan...')
    float_df = train_df[float64_col]
    float_df.fillna(float_df.median(), inplace=True)
    print('filled nan')
    # del cols which unique eq. 1
    float64_uniq_col = float_uniq(float_df, float64_col)
    float64_col = [col for col in float64_col if col not in \
                   float64_uniq_col]
    print('deleted unique cols, and float cols count:', len(float64_col))
    # obtained corrcoef greater than 0.2
    float64_col.remove('Y')
    y_train = train_df.Y.values
    corr_num = np.round(np.linspace(0.1, 0.2, 20), 2)
    test_scores = []
    num_scores = []
    print('get test data...')
    test_df = pd.read_excel('test_a.xlsx')
    corr_df = cal_corrcoef(float_df, y_train, float64_col)
    for num in corr_num:
        corr02 = corr_df[corr_df.corr_value >= num]
        corr02_col = corr02['col'].values.tolist()
        print('get x_train')
        x_train = float_df[corr02_col].values

        sub_test = test_df[corr02_col]
        sub_test.fillna(sub_test.median(), inplace=True)
        x_test = sub_test.values
        print('x_train shape:', x_train.shape)
        print('x_test shape:', x_test.shape)
        print('build model...')
        X = np.vstack((x_train, x_test))
        X = preprocessing.scale(X)
        x_train = X[0:len(x_train)]
        x_test = X[len(x_train):]
        alpha = find_min_alpha(x_train, y_train)
        model = create_model(x_train, y_train, alpha)
        print('predict and submit...')
        subA = model.predict(x_test)
        # read submit data
        # sub_df = pd.read_csv('sub_a.csv', header=None)
        # sub_df['Y'] = subA
        # sub_df.to_csv('final3.csv', header=None, index=False)
        print("交叉验证...")
        scores = cross_validation.cross_val_score(model, x_train, y_train, cv=10, scoring='neg_mean_squared_error')
        print(scores)
        print(str(num) + ":" + str(scores.mean()))
        num_scores.append([num, scores.mean()])
        test_scores.append(scores.mean())
    plt.plot(corr_num, test_scores)
    plt.title("cross val score")
    plt.xlabel("alpha")
    plt.ylabel('scores')
    plt.show()
    plt.savefig()
    print(sorted(num_scores, key=lambda x:x[1]))
