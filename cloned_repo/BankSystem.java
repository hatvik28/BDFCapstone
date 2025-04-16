import java.util.HashMap;
import java.util.Map;

public class BankSystem {
    private Map<Integer, Double> accounts = new HashMap<>();

    // Create a new account with a starting balance
    public void createAccount(int accountId, double initialBalance) {
        accounts.put(accountId, initialBalance);
    }

    // Deposit money into an account
    public void deposit(int accountId, double amount) {
        if (amount > 0) {
            accounts.put(accountId, accounts.get(accountId) + amount);
        }
    }

    // Withdraw money from an account (Bug: Allows negative balances)
    public void withdraw(int accountId, double amount) {
        if (amount > 0) {
            accounts.put(accountId, accounts.get(accountId) - amount); // No balance check
        }
    }

    // Transfer money from one account to another (Bug: No null checks)
    public void transfer(int fromAccount, int toAccount, double amount) {
        if (amount > 0) {
            withdraw(fromAccount, amount);
            deposit(toAccount, amount); // No check if `toAccount` exists
        }
    }

    // Calculate interest (Bug: Division by zero risk if balance is 0)
    public double calculateInterest(int accountId, double interestRate) {
        return accounts.get(accountId) * (interestRate / accounts.get(accountId)); // Risky
    }

    // Display account balance (Bug: No check if account exists)
    public void displayBalance(int accountId) {
        System.out.println("Account " + accountId + " Balance: $" + accounts.get(accountId));
    }

    public static void main(String[] args) {
        BankSystem bank = new BankSystem();
        bank.createAccount(101, 500);
        bank.createAccount(102, 1000);

        bank.deposit(101, 200);
        bank.withdraw(101, 100);
        bank.transfer(101, 102, 50);

        bank.displayBalance(101);
        bank.displayBalance(102);
    }
}
