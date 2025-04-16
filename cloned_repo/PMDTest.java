import java.util.Random;

public class PMDTest {

    // Unused variable (dead local store)
    private static final String UNUSED_CONSTANT = "I am not used";

    public static void main(String[] args) {
        // Null assignment leading to potential NullPointerException
        String name = null;
        if (name.equals("PMD")) { // This line can throw a NullPointerException
            System. out.println("Name matches PMD");
        }

        // Inefficient string concatenation in a loop
        String result = "";
        for (int i = 0; i < 100; i++) {
            result += i + ", "; // Inefficient, should use StringBuilder
        }
        System.out.println(result);

        // Avoid instantiating new objects inside a loop
        for (int i = 0; i < 10; i++) {
            Random random = new Random(); // Should not create new Random inside loop
            System.out.println(random.nextInt());
        }

        // Array Index Out of Bounds
        int[] array = {1, 2, 3};
        System.out.println(array[5]); // Accessing index out of bounds
    }
}
