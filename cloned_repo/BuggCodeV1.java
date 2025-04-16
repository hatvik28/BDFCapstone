public class BuggCodeV1 {

  public static void main(String[] args) {

    String str = null;
    int length = (str != null) ? str.length() : 0;

    int[] numbers = {1, 2, 3};
    System.out.println(numbers[2]);

    for (int i = 0; i < 5; i++) {
      System.out.println("Loop iteration: " + i);
    }

    final String text = "Buggy";
    if (text.length() > 10) {
      System.out.println(text.substring(10));
    } else {
      System.out.println("Substring index out of bounds");
    }

    boolean condition = false;
    if (condition) {
      System.out.println("This code is unreachable!");
    }
  }
}
