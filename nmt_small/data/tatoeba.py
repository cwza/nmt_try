# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_data.tatoeba.ipynb (unless otherwise specified).

__all__ = ['get_tatoeba_dss']

# Cell
from fastai2.basics import *
from transformers import AutoTokenizer

from fastai2_utils.data.all import *
from fastai_transformers_utils.all import *

# Cell
def _tokenize_data(ori_data_loc, enc_tokenizer, dec_tokenizer):
    df = pd.read_csv(ori_data_loc, header=None, names=['English', 'Chinese', 'Contributor'], delimiter='\t')
    df.drop(['Contributor'], axis=1, inplace=True)

    tok_df = df.copy()
    encoder_tok_list = L(parallel_gen(TransformersTokenizer, df.Chinese, tokenizer=enc_tokenizer)).sorted().itemgot(1)
    tok_df.Chinese =  encoder_tok_list.map(lambda x: ' '.join(x)) # split tokens by ' '
    decoder_tok_list = L(parallel_gen(TransformersTokenizer, df.English, tokenizer=dec_tokenizer)).sorted().itemgot(1)
    tok_df.English =  decoder_tok_list.map(lambda x: ' '.join(x)) # split tokens by ' '

    is_valid = np.zeros(len(tok_df))
    is_valid[:int(len(tok_df)*0.2)] = 1
    np.random.RandomState(42).shuffle(is_valid)
    is_valid = is_valid.astype(np.bool)
    tok_df['is_valid'] = is_valid

    return tok_df

# Cell
def get_tatoeba_dss(tok_data_loc, enc_tokenizer, dec_tokenizer, enc_seq_len, dec_seq_len, pct=1.0):
    tok_df = pd.read_csv(tok_data_loc)

    splits = ColSplitter()(tok_df)
    splits = pct_splits(splits, pct=pct)

    encoder_input_tfm = [attrgetter('Chinese'), lambda x: x.split(' '), TransformersNumericalize(enc_tokenizer), Pad2Max(enc_seq_len, enc_tokenizer.pad_token_id)]
    decoder_input_tfm = [attrgetter('English'), lambda x: x.split(' '), TransformersNumericalize(dec_tokenizer), Pad2Max(dec_seq_len+1, dec_tokenizer.pad_token_id), lambda x: x[:-1]]
    decoder_output_tfm = [attrgetter('English'), lambda x: x.split(' '), TransformersNumericalize(dec_tokenizer), Pad2Max(dec_seq_len+1, dec_tokenizer.pad_token_id), lambda x: x[1:]]
    ds_tfms = [
        encoder_input_tfm,
        decoder_input_tfm,
        decoder_output_tfm,
    ]

    dss = Datasets(tok_df, tfms=ds_tfms, splits=splits, n_inp=2)
    return dss