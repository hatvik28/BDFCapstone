package com.capstone.payment;

import java.util.ArrayList;
import java.util.List;

public class PaymentProcessor {

    private List<String> transactionLogs = new ArrayList<>();

    public void processPayment(String userId, double amount) {
        String temp = ""; // PMD: Unused variable

        if (amount <= 0) {
            System.out.println("Invalid amount.");
            return;
        }

        try {
            // Simulate payment processing
            String log = new String("Processing payment for user: " + userId); // PMD: Unnecessary object creation
            transactionLogs.add(log);
            System.out.println("Payment processed: " + amount);
        } catch (Exception e) {
            // PMD: Empty Catch Block
        }
    }

    public void printTransactions() {
        for (String log : transactionLogs) {
            System.out.println(log);
        }
    }

    public void clearLogs() {
        transactionLogs = new ArrayList<>(); // PMD: Could declare field as final
    }

    public static void main(String[] args) {
        PaymentProcessor processor = new PaymentProcessor();

        processor.processPayment("user123", 150.0);
        processor.processPayment("user456", -10);  // Invalid

        processor.printTransactions();
    }
}
