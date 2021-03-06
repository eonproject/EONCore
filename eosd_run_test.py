#!/usr/bin/python3

import testUtils

import argparse
import random

###############################################################
# eosd_run_test
###############################################################

Print=testUtils.Utils.Print

def errorExit(msg="", raw=False, errorCode=1):
    Print("ERROR:" if not raw else "", msg)
    exit(errorCode)

def cmdError(name, code=0, exitNow=False):
    msg="FAILURE - %s%s" % (name, ("" if code == 0 else (" returned error code %d" % code)))
    if exitNow:
        errorExit(msg, True)
    else:
        Print(msg)

TEST_OUTPUT_DEFAULT="test_output_0.txt"
LOCAL_HOST="localhost"
DEFAULT_PORT=8888
# INITA_PRV_KEY="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
# INITB_PRV_KEY="5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
#LOG_FILE="eeosd_run_test.log"

parser = argparse.ArgumentParser(add_help=False)
# Override default help argument so that only --help (and not -h) can call help
parser.add_argument('-?', action='help', default=argparse.SUPPRESS,
                    help=argparse._('show this help message and exit'))
parser.add_argument("-o", "--output", type=str, help="output file", default=TEST_OUTPUT_DEFAULT)
parser.add_argument("-h", "--host", type=str, help="eosd host name", default=LOCAL_HOST)
parser.add_argument("-p", "--port", type=str, help="eosd host port", default=DEFAULT_PORT)
parser.add_argument("--dumpErrorDetails",
                    help="Upon error print tn_data_*/config.ini and tn_data_*/stderr.log to stdout",
                    action='store_true')
parser.add_argument("--keepLogs", help="Don't delete tn_data_* folders upon test completion",
                    action='store_true')
parser.add_argument("-v", help="verbose logging", action='store_true')

args = parser.parse_args()
testOutputFile=args.output
server=args.host
port=args.port
# debug=args.v
debug=True
localTest=True if server == LOCAL_HOST else False
#testUtils.Utils.Debug=debug
#ciju
testUtils.Utils.Debug=True

cluster=testUtils.Cluster(walletd=True)
walletMgr=testUtils.WalletMgr(True)
cluster.killall()
cluster.cleanup()
walletMgr.killall()
walletMgr.cleanup()

random.seed(1) # Use a fixed seed for repeatability.
testSuccessful=False
dumpErrorDetails=args.dumpErrorDetails
keepLogs=args.keepLogs
killEosInstances=True

try:
    Print("BEGIN")
    print("TEST_OUTPUT: %s" % (testOutputFile))
    print("SERVER: %s" % (server))
    print("PORT: %d" % (port))

    if localTest:
        Print("Stand up cluster")
        if cluster.launch() is False:
            cmdError("launcher")
            errorExit("Failed to stand up eos cluster.")

    accounts=testUtils.Cluster.createAccountKeys(3)
    if accounts is None:
        errorExit("FAILURE - create keys")
    testeraAccount=accounts[0]
    testeraAccount.name="testera"
    currencyAccount=accounts[1]
    currencyAccount.name="currency"
    exchangeAccount=accounts[2]
    exchangeAccount.name="exchange"

    PRV_KEY1=testeraAccount.ownerPrivateKey
    PUB_KEY1=testeraAccount.ownerPublicKey
    PRV_KEY2=currencyAccount.ownerPrivateKey
    PUB_KEY2=currencyAccount.ownerPublicKey
    PRV_KEY3=exchangeAccount.activePrivateKey
    PUB_KEY3=exchangeAccount.activePublicKey
    
    testeraAccount.activePrivateKey=currencyAccount.activePrivateKey=PRV_KEY3
    testeraAccount.activePublicKey=currencyAccount.activePublicKey=PUB_KEY3

    exchangeAccount.ownerPrivateKey=PRV_KEY2
    exchangeAccount.ownerPublicKey=PUB_KEY2
    
    Print("Stand up walletd")
    if walletMgr.launch() is False:
        cmdError("eos-walletd")
        errorExit("Failed to stand up eos walletd.")

    testWalletName="test"
    Print("Creating wallet \"%s\"." % (testWalletName))
    testWallet=walletMgr.create(testWalletName)
    if testWallet is None:
        cmdError("eos wallet create")
        errorExit("Failed to create wallet %s." % (testWalletName))

    for account in accounts:
        Print("Importing keys for account %s into wallet %s." % (account.name, testWallet.name))
        if not walletMgr.importKey(account, testWallet):
            cmdError("eosc wallet import")
            errorExit("Failed to import key for account %s" % (account.name))

    initaWalletName="inita"
    Print("Creating wallet \"%s\"." % (initaWalletName))
    initaWallet=walletMgr.create(initaWalletName)
    if initaWallet is None:
        cmdError("eos wallet create")
        errorExit("Failed to create wallet %s." % (initaWalletName))
    
    initaAccount=testUtils.Cluster.initaAccount
    initbAccount=testUtils.Cluster.initbAccount

    Print("Importing keys for account %s into wallet %s." % (initaAccount.name, initaWallet.name))
    if not walletMgr.importKey(initaAccount, initaWallet):
        cmdError("eosc wallet import")
        errorExit("Failed to import key for account %s" % (initaAccount.name))

    Print("Locking wallet \"%s\"." % (testWallet.name))
    if not walletMgr.lockWallet(testWallet):
        cmdError("eosc wallet lock")
        errorExit("Failed to lock wallet %s" % (testWallet.name))

    Print("Unlocking wallet \"%s\"." % (testWallet.name))
    if not walletMgr.unlockWallet(testWallet):
        cmdError("eosc wallet unlock")
        errorExit("Failed to unlock wallet %s" % (testWallet.name))

    Print("Locking all wallets.")
    if not walletMgr.lockAllWallets():
        cmdError("eosc wallet lock_all")
        errorExit("Failed to lock all wallets")

    Print("Unlocking wallet \"%s\"." % (testWallet.name))
    if not walletMgr.unlockWallet(testWallet):
        cmdError("eosc wallet unlock")
        errorExit("Failed to unlock wallet %s" % (testWallet.name))

    Print("Getting open wallet list.")
    wallets=walletMgr.getOpenWallets()
    if len(wallets) == 0 or wallets[0] != testWallet.name or len(wallets) > 1:
        Print("FAILURE - wallet list did not include %s" % (testWallet.name))
        errorExit("Unexpected wallet list: %s" % (wallets))

    Print("Getting wallet keys.")
    actualKeys=walletMgr.getKeys()
    expectedkeys=[]
    for account in accounts:
        expectedkeys.append(account.ownerPrivateKey)
        expectedkeys.append(account.activePrivateKey)
    noMatch=list(set(expectedkeys) - set(actualKeys))
    if len(noMatch) > 0:
        errorExit("FAILURE - wallet keys did not include %s" % (noMatch), raw=true)

    Print("Locking all wallets.")
    if not walletMgr.lockAllWallets():
        cmdError("eosc wallet lock_all")
        errorExit("Failed to lock all wallets")

    Print("Unlocking wallet \"%s\"." % (initaWallet.name))
    if not walletMgr.unlockWallet(initaWallet):
        cmdError("eosc wallet unlock")
        errorExit("Failed to unlock wallet %s" % (testWallet.name))

    Print("Getting wallet keys.")
    actualKeys=walletMgr.getKeys()
    expectedkeys=[initaAccount.ownerPrivateKey]
    noMatch=list(set(expectedkeys) - set(actualKeys))
    if len(noMatch) > 0:
        errorExit("FAILURE - wallet keys did not include %s" % (noMatch), raw=true)
        
    node=cluster.getNode(0)
    if node is None:
        errorExit("Cluster in bad state, received None node")

    Print("Create new account %s via %s" % (testeraAccount.name, initaAccount.name))
    transId=node.createAccount(testeraAccount, initaAccount, waitForTransBlock=True)
    if transId is None:
        cmdError("eosc create account")
        errorExit("Failed to create account %s" % (testeraAccount.name))

    Print("Verify account %s" % (testeraAccount))
    if not node.verifyAccount(testeraAccount):
        errorExit("FAILURE - account creation failed.", raw=True)

    transferAmount=975321
    Print("Transfer funds %d from account %s to %s" % (transferAmount, initaAccount.name, testeraAccount.name))
    if node.transferFunds(initaAccount, testeraAccount, transferAmount, "test transfer") is None:
        cmdError("eosc transfer")
        errorExit("Failed to transfer funds %d from account %s to %s" % (
            transferAmount, initaAccount.name, testeraAccount.name))

    expectedAmount=transferAmount
    Print("Verify transfer, Expected: %d" % (expectedAmount))
    actualAmount=node.getAccountBalance(testeraAccount.name)
    if expectedAmount != actualAmount:
        cmdError("FAILURE - transfer failed")
        errorExit("Transfer verification failed. Excepted %d, actual: %d" % (expectedAmount, actualAmount))

    transferAmount=100
    Print("Force transfer funds %d from account %s to %s" % (
        transferAmount, initaAccount.name, testeraAccount.name))
    if node.transferFunds(initaAccount, testeraAccount, transferAmount, "test transfer", force=True) is None:
        cmdError("eosc transfer")
        errorExit("Failed to force transfer funds %d from account %s to %s" % (
            transferAmount, initaAccount.name, testeraAccount.name))

    expectedAmount=975421
    Print("Verify transfer, Expected: %d" % (expectedAmount))
    actualAmount=node.getAccountBalance(testeraAccount.name)
    if expectedAmount != actualAmount:
        cmdError("FAILURE - transfer failed")
        errorExit("Transfer verification failed. Excepted %d, actual: %d" % (expectedAmount, actualAmount))

    Print("Create new account %s via %s" % (currencyAccount.name, initbAccount.name))
    transId=node.createAccount(currencyAccount, initbAccount)
    if transId is None:
        cmdError("eosc create account")
        errorExit("Failed to create account %s" % (currencyAccount.name))

    Print("Create new account %s via %s" % (exchangeAccount.name, initaAccount.name))
    transId=node.createAccount(exchangeAccount, initaAccount, waitForTransBlock=True)
    if transId is None:
        cmdError("eosc create account")
        errorExit("Failed to create account %s" % (exchangeAccount.name))

    Print("Locking all wallets.")
    if not walletMgr.lockAllWallets():
        cmdError("eosc wallet lock_all")
        errorExit("Failed to lock all wallets")

    Print("Unlocking wallet \"%s\"." % (testWallet.name))
    if not walletMgr.unlockWallet(testWallet):
        cmdError("eosc wallet unlock")
        errorExit("Failed to unlock wallet %s" % (testWallet.name))

    transferAmount=975311
    Print("Transfer funds %d from account %s to %s" % (
        transferAmount, testeraAccount.name, currencyAccount.name))
    transId=node.transferFunds(testeraAccount, currencyAccount, transferAmount, "test transfer a->b")
    if transId is None:
        cmdError("eosc transfer")
        errorExit("Failed to transfer funds %d from account %s to %s" % (
            transferAmount, initaAccount.name, testeraAccount.name))

    expectedAmount=975311
    Print("Verify transfer, Expected: %d" % (expectedAmount))
    actualAmount=node.getAccountBalance(currencyAccount.name)
    if actualAmount is None:
        cmdError("eosc get account currency")
        errorExit("Failed to retrieve balance for account %s" % (currencyAccount.name))
    if expectedAmount != actualAmount:
        cmdError("FAILURE - transfer failed")
        errorExit("Transfer verification failed. Excepted %d, actual: %d" % (expectedAmount, actualAmount))

    expectedAccounts=[testeraAccount.name, currencyAccount.name, exchangeAccount.name]
    Print("Get accounts by key %s, Expected: %s" % (PUB_KEY3, expectedAccounts))
    actualAccounts=node.getAccountsByKey(PUB_KEY3)
    if actualAccounts is None:
        cmdError("eosc get accounts pub_key3")
        errorExit("Failed to retrieve accounts by key %s" % (PUB_KEY3))
    noMatch=list(set(expectedAccounts) - set(actualAccounts))
    if len(noMatch) > 0:
        errorExit("FAILURE - Accounts lookup by key %s. Expected: %s, Actual: %s" % (
            PUB_KEY3, expectedAccounts, actualAccounts), raw=True)

    expectedAccounts=[testeraAccount.name]
    Print("Get accounts by key %s, Expected: %s" % (PUB_KEY1, expectedAccounts))
    actualAccounts=node.getAccountsByKey(PUB_KEY1)
    if actualAccounts is None:
        cmdError("eosc get accounts pub_key1")
        errorExit("Failed to retrieve accounts by key %s" % (PUB_KEY1))
    noMatch=list(set(expectedAccounts) - set(actualAccounts))
    if len(noMatch) > 0:
        errorExit("FAILURE - Accounts lookup by key %s. Expected: %s, Actual: %s" % (
            PUB_KEY1, expectedAccounts, actualAccounts), raw=True)

    expectedServants=[testeraAccount.name, currencyAccount.name]
    Print("Get %s servants, Expected: %s" % (initaAccount.name, expectedServants))
    actualServants=node.getServants(initaAccount.name)
    if actualServants is None:
        cmdError("eosc get servants testera")
        errorExit("Failed to retrieve %s servants" % (initaAccount.name))
    noMatch=list(set(expectedAccounts) - set(actualAccounts))
    if len(noMatch) > 0:
        errorExit("FAILURE - %s servants. Expected: %s, Actual: %s" % (
            initaAccount.name, expectedServants, actualServants), raw=True)

    Print("Get %s servants, Expected: []" % (testeraAccount.name))
    actualServants=node.getServants(testeraAccount.name)
    if actualServants is None:
        cmdError("eosc get servants testera")
        errorExit("Failed to retrieve %s servants" % (testeraAccount.name))
    if len(actualServants) > 0:
        errorExit("FAILURE - %s servants. Expected: [], Actual: %s" % (
            testeraAccount.name, actualServants), raw=True)

    node.waitForTransIdOnNode(transId)

    Print("Get transaction details %s" % (transId))
    transaction=node.getTransactionDetails(transId)
    if transaction is None:
        cmdError("eosc get transaction trans_id")
        errorExit("Failed to retrieve transaction details %s" % (transId))

    if transaction.tType != "transfer" or transaction.amount != 975311:
        errorExit("FAILURE - get transaction trans_id failed: %s" % (transId), raw=True)

    Print("Get transactions for account %s" % (testeraAccount.name))
    actualTransactions=node.getTransactionsByAccount(testeraAccount.name)
    if actualTransactions is None:
        cmdError("eosc get transactions testera")
        errorExit("Failed to get transactions by account %s" % (testeraAccount.name))
    if len(actualTransactions) == 0:
        errorExit("FAILURE - get transactions testera failed", raw=True)

    Print("Get code hash for account %s" % (currencyAccount.name))
    codeHash=node.getAccountCodeHash(currencyAccount.name)
    if codeHash is None:
        cmdError("eosc get code currency")
        errorExit("Failed to get code hash for account %s" % (currencyAccount.name))
    nonZero=codeHash.replace('0', '')
    if nonZero != "":
        errorExit("FAILURE - get transactions testera failed", raw=True)

    # wastFile="contracts/currency/currency.wast"
    # abiFile="contracts/currency/currency.abi"
    # Print("Publish contract")
    # transId=node.publishContract(currencyAccount.name, wastFile, abiFile, waitForTransBlock=True)
    # if transId is None:
    #     cmdError("eosc set contract currency")
    #     errorExit("Failed to publish contract.")
        
    testSuccessful=True
    Print("END")
finally:
    if not testSuccessful and dumpErrorDetails:
        cluster.dumpErrorDetails()
        wallet.dumpErrorDetails()
        Utils.Print("== Errors see above ==")

    if killEosInstances:
        Print("Shut down the cluster and wallet.")
        cluster.killall()
        walletMgr.killall()
        if testSuccessful and not keepLogs:
            Print("Cleanup cluster and wallet data.")
            cluster.cleanup()
            walletMgr.cleanup()
    pass
    
exit(0)
