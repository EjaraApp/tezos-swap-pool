# tezos-swap-pool
Smart contract protocol to facilitate swapping of tezos with other cryptos like bitcoin and ethereum.

Read more here https://medium.com/ejara/a-smart-contract-scheme-to-swap-tezos-with-any-crypto-dbd5e038d992


## Endpoints 

```    
@sp.entry_point
def change_admin(self, params):
```
- Allows change of admin using spare

```
@sp.entry_point
def add_oracles(self, params):
```
- Allows adding of new oracles
  
```
@sp.entry_point
def remove_oracles(self, params):
```
- Allows removing of existing oracles
  
```
@sp.entry_point
def add_pool(self, cryptos):
```
- adds exchange request to the tezos open pool (user wants to swap their tezos for something else)
```
@sp.entry_point
def dip_pool(self, address, amount, crypto, rate):
```
- adds a swap request to the swap pool (user wants to swap something else for tezos)
- it allocates available tezos from the open pool

```
@sp.entry_point
def update_pool(self, updates):
```         
- oracle calls this endpoint to notify smart contract
- of the status of chain transfers
- tezos is transfered to off chain party's tezos account if oracle confirms

```
@sp.entry_point
def trim_pool(self):
```
- Remove all completed items from open to closed pool
- an item is comleted if timelock is up and no pending exchanges on it
- or if amount available for exchange has been exhausted

## Current Testnet Address of Contract 
### (KT1XNhpLMP3xGeQDjiHxfHiin93evqpssHA7)


## Tech Stack
- SmartPy to write smart contract (https://smartpy.io/)
- Tezos Taquito to interact with smart contract (https://tezostaquito.io/)

## TODO
- [x]  Complete Smart Contract (initial version)
- [x]  Deploy to Testnet.
- [ ]  Bitcoin Oracle. [Dec 18]
- [ ]  Ethereum Oracle. [Dec 25]
- [ ]  Run a Full Testnet Test. [Dec 31]
- [ ]  Short client script to interact with contract (mainly for mobile app integration) [Jan 8]
- [ ]  Mobile app V2 integration. [Jan 15]
