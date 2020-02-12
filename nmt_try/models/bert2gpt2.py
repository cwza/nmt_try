# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03c_models.bert2gpt2.ipynb (unless otherwise specified).

__all__ = ['gen_attention_mask', 'BertEncoder', 'BatchFirstMultiheadAttention', 'CrossAttention', 'GPT2Decoder',
           'Bert2GPT2', 'GeneratedBert2GPT2', 'generate_from_ids']

# Cell
from fastai2.basics import *

from transformers import AutoModel, AutoTokenizer, PreTrainedTokenizer

from fastai2_utils.pytorch.transformer import *
from fastai_transformers_utils.tokenizers import GPT2DecoderTokenizer
from fastai_transformers_utils.generated_lm import GeneratedLM, GenerateArgs

# Cell
def gen_attention_mask(inp_ids, pad_id):
    '''
        Returns Tensor where 0 are positions that contain pad_id, others 1.
        input_ids: (bs, seq_len) returns: (bs, seq_len)
    '''
    key_padding_mask = gen_key_padding_mask(inp_ids, pad_id)
    return (~key_padding_mask).long()

# Cell
class BertEncoder(nn.Module):
    def __init__(self, model_name):
        ''' model_name: pretrained bert model name from huggingface '''
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.layer_groups = [self.bert.embeddings, *self.bert.encoder.layer, self.bert.pooler]
    def forward(self, src_input_ids, src_attention_mask):
        '''
        src_input_ids: (bs, enc_seq_len)
        src_attention_mask: (bs, enc_seq_len)
        returns: (bs, enc_seq_len, embed_size)
        '''
        return self.bert(src_input_ids, attention_mask=src_attention_mask)[0]

# Cell
class BatchFirstMultiheadAttention(nn.MultiheadAttention):
    '''
        Pytorch wants your query, key, value be (seq_len, b, embed_dim) and return (seq_len, b, embed_dim)
        But I like batch-first thing. input: (b, seq_len, embed_dim) output: (b, seq_len, embed_dim)
    '''
    def forward(self, query, key, value, **kwargs):
        '''
        - inputs:
        - query: (bs, tgt_seq_len, embed_dim)
        - key: (bs, src_seq_len, embed_dim)
        - value: (bs, src_seq_len, embed_dim)

        - outputs:
        - attn_output: (bs, tgt_seq_len, embed_dim)
        - attn_weight: (bs, tgt_seq_len, src_seq_len), Averaged weights that averaged over all heads
        '''
        attn_output, attn_weight = super().forward(query.permute(1, 0, 2), key.permute(1, 0, 2), value.permute(1, 0, 2), **kwargs)
        return attn_output.permute(1, 0, 2), attn_weight

# Cell
class CrossAttention(nn.Module):
    def __init__(self, embed_dim, num_heads=1, drop_p=0, num_layers=1):
        super().__init__()
        self.cross_attn_layers = nn.ModuleList(
            [BatchFirstMultiheadAttention(embed_dim, num_heads=num_heads, dropout=drop_p) for _ in range(num_layers)]
        )
    def forward(self, tgt, src, src_key_padding_mask):
        '''
        tgt: (bs, tgt_seq_len, embed_size)
        src: (bs, src_seq_len, embed_size)
        src_key_padding_mask: (bs, src_seq_len)
        returns: output, attn_weight
            output: (bs, tgt_seq_len, embed_dim)
            attn_weight: (bs, tgt_seq_len, src_seq_len)
        '''
        for layer in self.cross_attn_layers:
            tgt, attn_weight = layer(tgt, src, src, key_padding_mask=src_key_padding_mask)
        return tgt, attn_weight

# Cell
def _adujsted_gpt2wte(gpt2):
    ''' Adjust pretrained gpt2 wte layer to adapt the GPT2DecoderTokenizer.
    Add bos_token and pad_token at the last of gpt2.wte.
    Use GPT2DecoderTokenizer or make sure the pad token is at the last of your tokenizer and the bos token is at the second-last.
    '''
    old_wte = gpt2.wte
    old_weight = old_wte.weight
    num_embeddings = old_wte.num_embeddings+2
    embedding_dim = old_wte.embedding_dim

    bos_weight = old_weight.mean(dim=0)[None] # (1, embedding_dim)
    pad_weight = torch.zeros((1, embedding_dim))

    new_weight = torch.cat([old_weight, bos_weight, pad_weight], dim=0) # (num_embeddings, embedding_dim)
    new_wte = nn.Embedding(num_embeddings, embedding_dim, padding_idx=num_embeddings-1)
    new_wte.weight.data = new_weight

    return new_wte

# Cell
class GPT2Decoder(nn.Module):
    def __init__(
        self,
        model_name, pad_id, # for GPT2
        vocab_size, # for classifier
        num_heads=1, drop_p=0, num_layers=1, # for CrossAttention
    ):
        ''' model_name: pretrained gpt2 model name from huggingface '''
        super().__init__()
        self.gpt2 = AutoModel.from_pretrained(model_name)
        self.gpt2.wte = _adujsted_gpt2wte(self.gpt2)
        self.cross_attn = CrossAttention(self.gpt2.config.n_embd, num_heads, drop_p, num_layers)
        self.classifier = nn.Linear(self.gpt2.config.n_embd, vocab_size)

        self.pad_id = pad_id
        self.layer_groups = [
            self.gpt2.wte, self.gpt2.wpe, *self.gpt2.h, self.gpt2.ln_f, *self.cross_attn.cross_attn_layers, self.classifier
        ]
    def forward(self, tgt_input_ids, memory, memory_key_padding_mask):
        '''
            tgt_input_ids: (bs, dec_seq_len)
            memory: (bs, enc_seq_len, embed_size)
            memory_key_padding_mask: (bs, enc_seq_len)
            returns: output, attn_weight
                output: (bs, dec_seq_len, dec_vocab_size)
                attn_weight: (bs, dec_seq_len, enc_seq_len)
        '''
        tgt_attention_mask = gen_attention_mask(tgt_input_ids, self.pad_id) # (bs, dec_seq_len)
        gpt2_out = self.gpt2(tgt_input_ids, attention_mask=tgt_attention_mask)[0] # (bs, dec_seq_len, 768)
        attn_output, attn_weight = self.cross_attn(gpt2_out, memory, src_key_padding_mask=memory_key_padding_mask) # (bs, dec_seq_len, 768), (bs, dec_seq_len, enc_seq_len)

        output = self.classifier(attn_output) # (bs, dec_seq_len, dec_vocab_size)

        return output, attn_weight

# Cell
class Bert2GPT2(nn.Module):
    def __init__(
        self,
        encoder: BertEncoder, decoder: GPT2Decoder,
        enc_pad_id, # for src_key_padding_mask and memory_key_padding_mask
    ):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.enc_pad_id = enc_pad_id
    def forward(self, src_input_ids, tgt_input_ids):
        '''
            src_input_ids: (bs, enc_seq_len)
            tgt_input_ids: (bs, dec_seq_len)
        '''
        src_attention_mask = gen_attention_mask(src_input_ids, self.enc_pad_id) # (bs, enc_seq_len)
        memory = self.encoder(src_input_ids, src_attention_mask) # (bs, enc_seq_len, embed_size)
        memory_key_padding_mask = (1-src_attention_mask).bool()
        output, _ = self.decoder(tgt_input_ids, memory, memory_key_padding_mask=memory_key_padding_mask) # (bs, dec_seq_len, embeded_size)

        return output

# Cell
class GeneratedBert2GPT2():
    def __init__(
        self,
        seq2seq: Bert2GPT2,
        enc_tokenizer: PreTrainedTokenizer,
        dec_tokenizer: PreTrainedTokenizer,
    ):
        self.seq2seq = seq2seq
        self.enc_tokenizer = enc_tokenizer
        self.dec_tokenizer = dec_tokenizer
        self.generatedLM = GeneratedLM(seq2seq.decoder, len(dec_tokenizer), dec_tokenizer.pad_token_id, [dec_tokenizer.eos_token_id], support_past=False)

# Cell
@patch
@torch.no_grad()
def generate_from_ids(self: GeneratedBert2GPT2, src_input_ids, generate_args: GenerateArgs):
    ''' src_input_ids: (bs, enc_seq_len), returns: (bs, max_length)'''
    self.seq2seq.eval()

    device = src_input_ids.device
    bs = src_input_ids.shape[0]
    tgt_input_ids = torch.zeros((bs, 1), dtype=torch.long, device=device).fill_(self.dec_tokenizer.bos_token_id) # (bs, 1)

    src_attention_mask = gen_attention_mask(src_input_ids, self.enc_tokenizer.pad_token_id) # (bs, enc_seq_len)
    memory = self.seq2seq.encoder(src_input_ids, src_attention_mask) # (bs, enc_seq_len, embed_size)
    memory_key_padding_mask = (1-src_attention_mask).bool()
    model_otherargs = self.generatedLM.build_model_otherargs_for_beam([memory, memory_key_padding_mask], generate_args.num_beams)

    result = self.generatedLM.generate(tgt_input_ids, generate_args, [model_otherargs[0]], dict(memory_key_padding_mask=model_otherargs[1]))

    return result