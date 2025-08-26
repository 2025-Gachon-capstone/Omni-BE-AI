import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class GELU(nn.Module):
    def forward(self, x):
        return 0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * x.pow(3))))


class LayerNorm(nn.Module):
    def __init__(self, features, eps=1e-6):
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(features))
        self.beta = nn.Parameter(torch.zeros(features))
        self.eps = eps

    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True)
        return self.gamma * (x - mean) / (std + self.eps) + self.beta


class SublayerConnection(nn.Module):
    def __init__(self, size, dropout):
        super().__init__()
        self.norm = LayerNorm(size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, sublayer):
        return x + self.dropout(sublayer(self.norm(x)))


class PositionwiseFeedForward(nn.Module):
    def __init__(self, d_model, d_ff, dropout=0.1):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)
        self.activation = GELU()

    def forward(self, x):
        return self.linear2(self.dropout(self.activation(self.linear1(x))))


class Attention(nn.Module):
    def forward(self, query, key, value, mask=None, dropout=None):
        d_k = query.size(-1)
        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        p_attn = F.softmax(scores, dim=-1)
        if dropout is not None:
            p_attn = dropout(p_attn)
        return torch.matmul(p_attn, value), p_attn


class MultiHeadedAttention(nn.Module):
    def __init__(self, h, d_model, dropout=0.1):
        super().__init__()
        assert d_model % h == 0
        self.d_k = d_model // h
        self.h = h
        self.linears = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(4)])
        self.attn = Attention()
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, query, key, value, mask=None):
        batch_size = query.size(0)
        query, key, value = [
            lin(x).view(batch_size, -1, self.h, self.d_k).transpose(1, 2)
            for lin, x in zip(self.linears, (query, key, value))
        ]
        x, attn = self.attn(query, key, value, mask=mask, dropout=self.dropout)
        x = x.transpose(1, 2).contiguous().view(batch_size, -1, self.h * self.d_k)
        return self.linears[-1](x)


class TransformerBlock(nn.Module):
    def __init__(self, hidden, attn_heads, feed_forward_hidden, dropout):
        super().__init__()
        self.attention = MultiHeadedAttention(h=attn_heads, d_model=hidden, dropout=dropout)
        self.feed_forward = PositionwiseFeedForward(d_model=hidden, d_ff=feed_forward_hidden, dropout=dropout)
        self.input_sublayer = SublayerConnection(size=hidden, dropout=dropout)
        self.output_sublayer = SublayerConnection(size=hidden, dropout=dropout)
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x, mask):
        x = self.input_sublayer(x, lambda _x: self.attention(_x, _x, _x, mask))
        x = self.output_sublayer(x, self.feed_forward)
        return self.dropout(x)


class TokenEmbedding(nn.Embedding):
    def __init__(self, vocab_size, embed_size):
        super().__init__(vocab_size, embed_size, padding_idx=0)
        self.weight.data.uniform_(-0.02, 0.02)


class InstacartEmbedding(nn.Module):
    def __init__(self, args):
        super().__init__()
        self.token_embed = TokenEmbedding(args.vocab_size, args.hidden_size)
        self.reordered_embed = TokenEmbedding(3, args.hidden_size)
        self.hour_embed = TokenEmbedding(25, args.hidden_size)
        self.aisle_embed = TokenEmbedding(args.aisle_size, args.hidden_size)
        self.dept_embed = TokenEmbedding(args.dept_size, args.hidden_size)
        self.count_bucket_embed = TokenEmbedding(args.count_bucket_size, args.hidden_size)
        self.position_embed = TokenEmbedding(args.max_seq_length, args.hidden_size)
        self.dropout = nn.Dropout(p=args.hidden_dropout_prob)

    def forward(self, input_ids, reordered, hour, aisle, dept, count_bucket, positions):
        x = self.token_embed(input_ids)
        x += self.reordered_embed(reordered)
        x += self.hour_embed(hour)
        x += self.aisle_embed(aisle)
        x += self.dept_embed(dept)
        x += self.count_bucket_embed(count_bucket)
        x += self.position_embed(positions)
        return self.dropout(x)


class InstacartBERT(nn.Module):
    def __init__(self, args):
        super().__init__()
        self.embedding = InstacartEmbedding(args)
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(args.hidden_size, args.num_attention_heads, args.hidden_size * 4, args.hidden_dropout_prob)
            for _ in range(args.num_hidden_layers)
        ])

    def forward(self, input_ids, reordered, hour, aisle, dept, count_bucket, positions):

        mask = (input_ids > 0).unsqueeze(1).repeat(1, input_ids.size(1), 1).unsqueeze(1)
        x = self.embedding(input_ids, reordered, hour, aisle, dept, count_bucket, positions)
        for transformer in self.transformer_blocks:
            x = transformer(x, mask)
        return x
