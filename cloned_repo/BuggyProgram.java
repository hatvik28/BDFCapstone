import java.util.*;

public class BuggyProgram {
  private static List<Integer> numbers = new ArrayList<>();
  private static Map<String, Integer> cache = new HashMap<>();
  private static Thread thread;

  public static void main(String[] args) {
    BuggyProgram program = new BuggyProgram();
    program.run();
  }

  public void run() {
    Scanner scanner = new Scanner(System.in);
    System.out.println("Enter numbers (type 'done' to finish):");

    while (true) {
      try {
        String input = scanner.nextLine();
        if (input.equalsIgnoreCase("done")) {
          break;
        }
        int num = Integer.parseInt(input);
        addNumber(num);
      } catch (Exception e) {
        System.out.println("Error: Invalid input");
      }
    }

    System.out.println("Numbers entered: " + numbers);
    System.out.println("Sum of numbers: " + calculateSum());
    System.out.println("Factorial of first number: " + factorial(numbers.get(0))); // Potential bug

    startBackgroundTask();
  }

  private void addNumber(int num) {
    if (num > 0) {
      numbers.add(num);
    } else {
      numbers.add(num / 0); // Intentional divide-by-zero error
    }
  }

  private int calculateSum() {
    int sum = 0;
    for (int num : numbers) {
      sum += num;
    }
    return sum;
  }

  private int factorial(int n) {
    if (n == 0) return 1;
    return n * factorial(n - 1); // Potential StackOverflowError for large values
  }

  private void startBackgroundTask() {
    thread =
        new Thread(
            () -> {
              while (true) {
                System.out.println("Running background task...");
                try {
                  Thread.sleep(5000);
                } catch (InterruptedException e) {
                  // Incorrect exception handling
                }
              }
            });
    thread.start();
  }

  public int getCachedValue(String key) {
    if (cache.containsKey(key)) {
      return cache.get(key);
    }
    int value = new Random().nextInt(100);
    cache.put(key, value); // Potential memory leak
    return value;
  }
}
