import smartpy as sp


class SwapPool(sp.Contract):

    def __init__(self, oracles, admin, spare, min_lock, cryptos_symbols, timelocks):

        open_pool_data = {
            'cryptos': sp.TMap(sp.TString, sp.TString),
            'amount': sp.TMutez,
            'timestamp': sp.TTimestamp,
            'timelock': sp.TTimestamp,
            'dips': sp.TMap(sp.TNat, sp.TRecord(amount = sp.TMutez, sent = sp.TBool))
        }

        swap_pool_data = {
            'address': sp.TAddress,
            'amount': sp.TMutez,
            'crypto': sp.TString,
            'rate': sp.TMutez,
            'timestamp': sp.TTimestamp,
            'timelock': sp.TTimestamp,
            'swaps': sp.TList(sp.TNat),
            'swapped': sp.TBool,
            'settled': sp.TMutez
        }

        self.init(
            spare=spare,
            admin=admin,
            oracles = oracles,
            accepted_cryptos = cryptos_symbols,
            min_lock = min_lock,
            timelocks = timelocks,
            pool_counter=sp.nat(0),
            swap_counter=sp.nat(0),
            open_pool = sp.map(tkey=sp.TNat, tvalue=sp.TRecord(**open_pool_data)),
            swap_pool = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(**swap_pool_data)),
            closed_pool = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(**open_pool_data))
        )

    def assert_oracle(self):
        sp.verify(self.data.oracles.contains(sp.sender), 'Invalid Oracle!')
    
    def assert_admin(self):
        sp.verify_equal(self.data.admin, sp.sender, 'Invalid Admin!')

    def assert_spare(self):
        sp.verify_equal(self.data.spare, sp.sender, 'Invalid Spare!')
    
    def assert_crypto(self, cryptos):
        sp.for crypto in cryptos:
            sp.verify(self.data.accepted_cryptos.contains(crypto), 'Invalid Crypto!')
    
    @sp.entry_point
    def change_admin(self, params):
        self.assert_spare()
        self.data.admin = params.admin

    @sp.entry_point
    def add_oracles(self, params):
        self.assert_admin()
        
        sp.for oracle in params.oracles.keys():
            self.data.oracles[oracle] = params.oracles[oracle]
    
    @sp.entry_point
    def remove_oracles(self, params):
        self.assert_admin()
        
        sp.for oracle in params.oracles:
            sp.if self.data.oracles.contains(oracle):
                del self.data.oracles[oracle]

    @sp.entry_point
    def add_pool(self, cryptos):
        # adds exchange request to the tezos open pool
        
        sp.verify(sp.amount > sp.tez(1), 'A minimum of 1 XTZ!')
        
        self.assert_crypto(cryptos.keys())
        
        self.data.open_pool[self.data.pool_counter] = sp.record(
            cryptos = cryptos,
            amount = sp.amount,
            timestamp = sp.now,
            timelock = sp.now.add_days(self.data.min_lock),
            dips = sp.map()
        )
        
        self.data.pool_counter = self.data.pool_counter + sp.nat(1)
        
    
    @sp.entry_point
    def dip_pool(self, address, amount, crypto, rate):
        # adds a swap request to the swap pool
        # it allocates available tezos from the open pool

        self.assert_crypto([crypto])

        y = sp.local('y', sp.map())
        s = sp.local('s', amount)

        # TODO: How to break out of this loop
        sp.for k in self.data.open_pool.keys():

            sp.if self.data.open_pool[k].cryptos.contains(crypto):
                # compte how much kTH pool request can provide (x)
                x = sp.local('x', self.data.open_pool[k].amount)
                sp.for j in self.data.open_pool[k].dips.keys():
                    sp.if (self.data.swap_pool[j].timelock > sp.now) | self.data.swap_pool[j].swapped:
                        x.value = x.value - self.data.open_pool[k].dips[j].amount

                sp.if x.value > sp.mutez(0):
                    sp.if s.value > sp.mutez(0):
                        sp.if x.value <= s.value:
                            y.value[k] = x.value
                        sp.else:
                            y.value[k] = s.value
                        s.value = s.value - x.value

                # need to break out of loop when s.value <= sp.mutez(0):

        sp.verify(s.value <= sp.mutez(0), 'Could not satify exchange request!')
        
        sp.for t in y.value.keys():
            self.data.open_pool[t].dips[self.data.swap_counter] = sp.record(amount = y.value[t], sent = False)
        
        self.data.swap_pool[self.data.swap_counter] = sp.record(
            address = address,
            crypto = crypto,
            amount = amount,
            rate = rate,
            timestamp = sp.now,
            timelock = sp.now.add_minutes(self.data.timelocks[crypto]),
            swaps = y.value.keys(),
            swapped = False,
            settled = sp.mutez(0)
        )
        
        self.data.swap_counter = self.data.swap_counter + sp.nat(1)
    
    @sp.entry_point
    def update_pool(self, updates):
        # oracle calls this endpoint to notify smart contract
        # of the status of chain transfers
        # tezos is transfered to off chain party's tezos account if oracle confirms
        self.assert_oracle()
        
        sp.for update in updates:
            sp.if (update['is_sent'] == 1) & ~self.data.open_pool[update['open_key']].dips[update['swap_key']].sent:
                sp.send(
                    self.data.swap_pool[update['swap_key']].address,
                    self.data.open_pool[update['open_key']].dips[update['swap_key']].amount,
                )
                
                self.data.swap_pool[update['swap_key']].settled = self.data.swap_pool[update['swap_key']].settled + self.data.open_pool[update['open_key']].dips[update['swap_key']].amount
                
                self.data.open_pool[update['open_key']].dips[update['swap_key']].sent = True
                
                sp.if self.data.swap_pool[update['swap_key']].settled == self.data.swap_pool[update['swap_key']].amount:
                    self.data.swap_pool[update['swap_key']].swapped = True
                
                
    
    @sp.entry_point
    def trim_pool(self, params):
        # Remove all completed items from open to closed pool
        # an item is comleted if timelock is up and no pending exchanges on it
        # or if amount available for exchange has been exhausted
        self.assert_oracle()


@sp.add_test(name = "Swap Pool Test")
def test():
    sc = sp.test_scenario()
    
    btc = sp.test_account('Ejara Bitcoin Oracle')
    admin = sp.test_account('Ejara Admin')
    spare = sp.test_account('Ejara Spare')

    oracles = {
        btc.address: 'Ejara Bitcoin Oracle'
    }
    
    cryptos_symbols = {'BTC': 'Bitcoin', 'ETH': 'Ethereum'}
    
    min_lock = 1
    
    timelocks = {
        'BTC': 60,
        'ETH': 30
    }
    
    c = SwapPool(oracles, admin.address, spare.address, min_lock, cryptos_symbols, timelocks)
    
    # c.set_initial_balance(sp.tez(100))
    
    sc += c
    
    xchngr = sp.test_account('List tezos on exchange')
    
    sc.h2('Add Pool Request!')
    
    open_pool_request = {
        'cryptos': {'BTC': '1Kf9gGLaCh8A6aNeg8a5Ewb7eEm63u8yYZ', 'ETH': '0x2028aa76C84802cd61Ab3BeC4f142ca33743068b'},
        'amount': sp.mutez(13*1000000),
    }
    
    sc += c.add_pool(
        open_pool_request['cryptos'],
    ).run(sender=xchngr.address, amount=sp.tez(13))
    
    sc += c.add_pool(
        open_pool_request['cryptos'],
    ).run(sender=xchngr.address, amount=sp.tez(13))
    
    sc.h2('Dip Pool Request!')
    
    offchainer = sp.test_account('Change my coin for tezos')
    
    swap_pool_request = {
        'address': offchainer.address,
        'amount': sp.tez(19),
        'crypto': 'BTC',
        'rate': sp.mutez(8600630000)
    }
    
    sc += c.dip_pool(
        address = swap_pool_request['address'],
        amount = swap_pool_request['amount'],
        crypto = swap_pool_request['crypto'],
        rate = swap_pool_request['rate'],
    )
    
    sc += c.dip_pool(
        address = swap_pool_request['address'],
        amount = sp.tez(7), #swap_pool_request['amount'],
        crypto = swap_pool_request['crypto'],
        rate = swap_pool_request['rate'],
    )
    
    sc.h2('Dip should fail!')
    
    sc += c.dip_pool(
        address = swap_pool_request['address'],
        amount = sp.mutez(7000000), #swap_pool_request['amount'],
        crypto = swap_pool_request['crypto'],
        rate = swap_pool_request['rate'],
    ).run(valid=False)
    
    sc.h2('Update Pool Request!')
    
    update_pool_data = [
        {
            'open_key': 0,
            'swap_key': 0,
            'is_sent': 1,
        },
        {
            'open_key': 1,
            'swap_key': 0,
            'is_sent': 0,
        },
        {
            'open_key': 1,
            'swap_key': 1,
            'is_sent': 1,
        },
    ]
    
    sc += c.update_pool(update_pool_data).run(sender =  btc.address)
    
    update_pool_data1 = [
        {
            'open_key': 1,
            'swap_key': 0,
            'is_sent': 1,
        }
    ]
    
    sc += c.update_pool(update_pool_data1).run(sender =  btc.address)
    
    
    
    
    
@sp.add_test(name = "Swap Pool Init")
def test():
    sc = sp.test_scenario()
    
    btc = sp.address('tz1d1sJVHi4vmD45CMVUtsm5itnQiNRULTuq')
    eth = sp.address('tz1UprVhwoHVrKodvFKcBBvqvsMiNB8HUyGC')
    admin = sp.address('tz1UprVhwoHVrKodvFKcBBvqvsMiNB8HUyGC')
    spare = sp.address('tz1UprVhwoHVrKodvFKcBBvqvsMiNB8HUyGC')

    oracles = {
        btc: 'Ejara Bitcoin Oracle',
        eth: 'Ejara Ethereum Oracle'
    }
    
    cryptos_symbols = {'BTC': 'Bitcoin', 'ETH': 'Ethereum'}
    
    min_lock = 1
    
    timelocks = {
        'BTC': 60,
        'ETH': 30
    }
    
    c = SwapPool(oracles, admin, spare, min_lock, cryptos_symbols, timelocks)
    
    # c.set_initial_balance(sp.tez(100))
    
    sc += c
    
    update_pool_data1 = [
        {
            'open_key': 1,
            'swap_key': 0,
            'is_sent': 1,
        }
    ]
    
    sc += c.update_pool(update_pool_data1).run(sender =  btc, valid= False)
