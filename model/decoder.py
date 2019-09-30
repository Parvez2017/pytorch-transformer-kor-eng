import torch
import torch.nn as nn

from model.attention import MultiHeadAttention
from model.positionwise import PositionWiseFeedForward


class DecoderLayer(nn.Module):
    def __init__(self, params):
        super(DecoderLayer, self).__init__()
        self.layer_norm = nn.LayerNorm(params.hidden_dim)

        self.self_attention = MultiHeadAttention(params)
        self.encoder_attention = MultiHeadAttention(params)
        self.position_wise_ffn = PositionWiseFeedForward(params)

    def forward(self, target, encoder_output, target_mask, dec_enc_mask):
        # target          = [batch size, target sentence length, hidden dim]
        # encoder_output  = [batch size, source sentence length, hidden dim]
        # target_mask     = [batch size, target sentence length, target sentence length]
        # dec_enc_mask    = [batch size, target sentence length, source sentence length]

        # Apply 'Add & Normalize' self attention, Encoder's Self attention and Position wise Feed Forward Network
        output = self.layer_norm(target + self.self_attention(target, target, target, target_mask))

        # In Decoder stack, query is the output from below layer and key & value are the output from the Encoder
        output = self.layer_norm(output + self.encoder_attention(output, encoder_output, encoder_output, dec_enc_mask))
        output = self.layer_norm(output + self.position_wise_ffn(output))
        # output = [batch size, target length, hidden dim]

        return output


class Decoder(nn.Module):
    def __init__(self, params):
        super(Decoder, self).__init__()
        self.device = params.device

        self.token_embedding = nn.Embedding(params.output_dim, params.hidden_dim)
        self.position_embedding = nn.Embedding(1000, params.hidden_dim)

        self.decoder_layers = nn.ModuleList([DecoderLayer(params) for _ in range(params.n_layer)])

        self.fc = nn.Linear(params.hidden_dim, params.output_dim)
        self.dropout = nn.Dropout(params.dropout)
        self.scale = torch.sqrt(torch.FloatTensor([params.hidden_dim])).to(self.device)

    def forward(self, target, source, target_mask, dec_enc_mask):
        # target          = [batch size, target sentence length]
        # source          = [batch size, source sentence length]
        # target_mask     = [batch size, target sentence length, target sentence length]
        # dec_enc_mask    = [batch size, target sentence length, source sentence length]

        # print(f'[D] Before embedding: {target.shape}')
        embedded = self.token_embedding(target)
        # print(f'[D] Before embedding: {embedded.shape}')
        position = torch.arange(0, target.shape[1]).unsqueeze(0).repeat(target.shape[0], 1).to(self.device)

        target = self.dropout(embedded + self.position_embedding(position))

        for decoder_layer in self.decoder_layers:
            target = decoder_layer(target, source, target_mask, dec_enc_mask)
        # target = [batch size, target length, hidden dim]
        # print(f'[D] After decoding: {target.shape}')
        output = self.fc(target)
        # output = [batch size, target length, output dim]
        # print(f'[D] After predicting: {output.shape}')
        # print('------------------------------------------------------------')
        return output
