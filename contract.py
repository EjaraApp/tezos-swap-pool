import smartpy as sp


class SwapPool(sp.Contract):

    def __init__(self, oracles, admin, spare, min_lock, cryptos_symbols):

        open_pool_data = {
            'cryptos': sp.TMap(sp.TString, sp.TString),
            'amount': sp.TMutez,
            'timestamp': sp.TTimestamp,
            'timelock': sp.TTimestamp,
            'dips': sp.TList(sp.TRecord(**{'swap': sp.TString, 'amount': sp.TMutez}))
        }

        closed_pool_data = {
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
            open_pool = sp.map(tkey=sp.TString, tvalue=sp.TRecord(**open_pool_data)),
            swap_pool = sp.big_map(tkey=sp.TString, tvalue=sp.TRecord(**closed_pool_data)),
            closed_pool = sp.big_map()
            )

    def assert_oracle(self):
        sp.verify(self.data.oracles.contains(sp.sender), 'Invalid Oracle!')
    
    def assert_admin(self):
        sp.verify_equal(self.data.admin, sp.sender, 'Invalid Admin!')

    def assert_spare(self):
        sp.verify_equal(self.data.spare, sp.sender, 'Invalid Spare!')
    
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
    def request_tezos_exchange(self, params):
        # adds exchange request to the tezos open pool
        pass
    
    @sp.entry_point
    def request_tezos_swap(self, params):
        # adds a swap request to the swap pool
        # it allocates available tezos from the open pool
        pass
    
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
    
    cryptos_symbols = ['BTC', 'ETH']
    
    min_lock = 1
    
    c = SwapPool(oracles, admin.address, spare.address, min_lock, cryptos_symbols)
    
    sc += c
