import smartpy as sp


class SwapPool(sp.Contract):

    def __init__(self, oracles, admin, spare, min_lock, cryptos_symbols, timelocks):

        open_pool_data = {
            'cryptos': sp.TMap(sp.TString, sp.TString),
            'amount': sp.TMutez,
            'timestamp': sp.TTimestamp,
            'timelock': sp.TTimestamp,
            'dips': sp.TList(sp.TRecord(**{'swap': sp.TString, 'amount': sp.TMutez}))
        }

        swap_pool_data = {
            'address': sp.TAddress,
            'amount': sp.TMutez,
            'crypto': sp.TString,
            'timestamp': sp.TTimestamp,
            'timelock': sp.TTimestamp,
            'swaps': sp.TList(sp.TString),
            'swapped': sp.TBool
        }

        self.init(
            spare=spare,
            admin=admin,
            oracles = oracles,
            accepted_cryptos = cryptos_symbols,
            min_lock = min_lock,
            timelocks = timelocks,
            open_pool = sp.map(tkey=sp.TString, tvalue=sp.TRecord(**open_pool_data)),
            swap_pool = sp.big_map(tkey=sp.TString, tvalue=sp.TRecord(**swap_pool_data)),
            closed_pool = sp.big_map()
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
    def request_tezos_exchange(self, cryptos, amount, key):
        # adds exchange request to the tezos open pool
        
        self.assert_crypto(cryptos.keys())
        
        sp.verify(~self.data.open_pool.contains(key), 'Key Exists!')
        
        self.data.open_pool[key] = sp.record(
            cryptos = cryptos,
            amount = amount,
            timestamp = sp.now,
            timelock = sp.now.add_days(self.data.min_lock),
            dips = sp.list()
        )
        
    
    @sp.entry_point
    def request_tezos_swap(self, address, amount, crypto, key):
        # adds a swap request to the swap pool
        # it allocates available tezos from the open pool
        
        self.assert_crypto([crypto])
        
        sp.verify(~self.data.swap_pool.contains(key), 'Key Exists!')
        
        self.data.swap_pool[key] = sp.record(
            address = address,
            crypto = crypto,
            amount = amount,
            timestamp = sp.now,
            timelock = sp.now.add_minutes(self.data.timelocks[crypto]),
            swaps = sp.list(),
            swapped = False
        )
    
    @sp.entry_point
    def update_pool(self, params):
        # oracle calls this endpoint to notify smart contract
        # of the status of chain transfers
        # tezos is transfered to off chain party's tezos account if oracle confirms
        self.assert_oracle()
    
    @sp.entry_point
    def clean_pool(self, params):
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
    
    sc += c
    
    exchanger = sp.test_account('List tezos on exchange')
    
    open_pool_request = {
        'cryptos': {'BTC': '1Kf9gGLaCh8A6aNeg8a5Ewb7eEm63u8yYZ'},
        'amount': sp.tez(13),
    }
    
    sc += c.request_tezos_exchange(
        cryptos = open_pool_request['cryptos'],
        amount = open_pool_request['amount'],
        key = 'asdf')
    
    swap_pool_request = {
            'address': exchanger.address,
            'amount': sp.tez(9),
            'crypto': 'BTC',
        }
    
    sc += c.request_tezos_swap(
        address = swap_pool_request['address'],
        amount = swap_pool_request['amount'],
        crypto = swap_pool_request['crypto'],
        key = 'jkl')
    
    