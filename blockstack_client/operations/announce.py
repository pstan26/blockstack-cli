#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Blockstack-client
    ~~~~~
    copyright: (c) 2014-2015 by Halfmoon Labs, Inc.
    copyright: (c) 2016 by Blockstack.org

    This file is part of Blockstack-client.

    Blockstack-client is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Blockstack-client is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with Blockstack-client. If not, see <http://www.gnu.org/licenses/>.
"""

import pybitcoin
from pybitcoin import embed_data_in_blockchain, make_op_return_tx, make_op_return_outputs, \
        make_op_return_script, broadcast_transaction, serialize_transaction, \
        make_pay_to_address_script

from pybitcoin.transactions.outputs import calculate_change_amount
from utilitybelt import is_hex
from binascii import hexlify, unhexlify

from ..b40 import b40_to_hex, bin_to_b40, is_b40
from ..config import *
from ..scripts import *

import virtualchain
log = virtualchain.get_logger("blockstack-client")

def build(message_hash):
    """
     
    Record format:
    
    0    2  3                             23
    |----|--|-----------------------------|
    magic op   message hash (160-bit)
    
    """
   
    if len(message_hash) != 40:
        raise Exception("Invalid hash: not 20 bytes")

    if not is_hex(message_hash):
        raise Exception("Invalid hash: not hex")

    readable_script = "ANNOUNCE 0x%s" % (message_hash)
    hex_script = blockstack_script_to_hex(readable_script)
    packaged_script = add_magic_bytes(hex_script)
    
    return packaged_script 


def make_outputs( data, inputs, change_address, tx_fee ):
    """
    Make outputs for an announcement.
    Raise ValueError if there are not enough inputs to make the transaction
    """

    dust_fee = (len(inputs) + 1) * DEFAULT_DUST_FEE + DEFAULT_OP_RETURN_FEE + tx_fee
    op_fee = DEFAULT_DUST_FEE
    dust_value = DEFAULT_DUST_FEE
    
    return [
        # main output
        {"script_hex": make_op_return_script(str(data), format='hex'),
         "value": 0},
        
        # change output
        {"script_hex": virtualchain.make_payment_script(change_address),
         "value": calculate_change_amount(inputs, op_fee, dust_fee)}
    ]


def make_transaction(message_hash, payment_addr, blockchain_client, tx_fee=0):
    
    message_hash = str(message_hash)
    payment_addr = str(payment_addr)
    tx_fee = int(tx_fee)

    # sanity check 
    if len(message_hash) != 40:
        raise Exception("Invalid message hash: not 20 bytes")

    if not is_hex( message_hash ):
        raise Exception("Invalid message hash: not hex")
    
    inputs = None
    private_key_obj = None
    
    inputs = tx_get_unspents( payment_addr, blockchain_client )
    nulldata = build(message_hash)
    outputs = make_outputs( nulldata, inputs, payment_addr, tx_fee )
   
    return (inputs, outputs)


def get_fees( inputs, outputs ):
    """
    Given a transaction's outputs, look up its fees:
    * there should be two outputs: the OP_RETURN and change address
    
    Return (dust fees, operation fees) on success 
    Return (None, None) on invalid output listing
    """
    if len(outputs) != 2:
        return (None, None)
    
    # 0: op_return
    if not tx_output_is_op_return( outputs[0] ):
        return (None, None) 
    
    if outputs[0]["value"] != 0:
        return (None, None) 
    
    # 1: change address 
    if virtualchain.script_hex_to_address( outputs[1]["script_hex"] ) is None:
        return (None, None)
    
    dust_fee = (len(inputs) + 1) * DEFAULT_DUST_FEE + DEFAULT_OP_RETURN_FEE
    op_fee = 0
    
    return (dust_fee, op_fee)


def snv_consensus_extras( new_name_rec, block_id, blockchain_name_data ):
    """
    Calculate any derived missing data that goes into the check() operation,
    given the block number, the name record at the block number, and the db.
    """
    return {}
