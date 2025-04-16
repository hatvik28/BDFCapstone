import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Calendar;
import java.util.GregorianCalendar;


public class BuggCodeFix {
 
  public static void main(String[] args) {
 
    String str = "Hello World";
    int length = str.length();
 
    int[] numbers = {1, 2, 3};
    System.out.println(numbers[2]);
 
    Object obj = "hello";
    String stri = (String) obj;
    System.out.println(stri);
 
    int i = 0;
    while (i < 10) {
      System.out.println("Finite Loop!");
      i++;
    }
 
    String text = "Buggy";
    if (text.length() > 10) {
      System.out.println(text.substring(10));
    } else {
      System.out.println("The string is not long enough to substring at index 10");
    }
 
    if (1 == 2) {
      System.out.println("This code is unreachable!");
    }
  }
}
