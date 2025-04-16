import java.awt.*;
import javax.swing.*;

public class BuggCode {

  public static void main(String[] args) {

    final String str = "Hello, World!";
    int length = str.length();
    System.out.println("Length of the string: " + length);

    int[] numbers = {1, 2, 3};

    System.out.println(numbers[2]);

    int i = 0;
    while (i < 5) {
      System.out.println("Loop iteration: " + i);
      i++;
    }

    String text = "Buggy";
    System.out.println(text);

    if (1 == 2) {
      System.out.println("This code is unreachable!");
    }
  }
}
