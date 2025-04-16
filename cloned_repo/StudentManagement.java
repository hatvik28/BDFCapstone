import java.io.*;
import java.util.*;

public class StudentManagement {
    private Map<Integer, Student> students = new HashMap<>();
    private Random random = new Random(); // Bug: Inefficient usage inside methods

    // Adds a new student
    public void addStudent(int id, String name, double gpa) {
        students.put(id, new Student(id, name, gpa));
    }

    // Displays student info (Bug: Possible NullPointerException if student ID is invalid)
    public void displayStudent(int id) {
        Student student = students.get(id);
        System.out.println("Student: " + student.name + ", GPA: " + student.gpa); // NP_NULL_ON_SOME_PATH_EXCEPTION
    }

    // Calculates average GPA (Bug: No students check, division by zero)
    public double calculateAverageGPA() {
        double total = 0;
        for (Student student : students.values()) {
            total += student.gpa;
        }
        return total / students.size(); // Division by zero if no students exist
    }

    // Reads student data from a file (Bug: No encoding specified, which can cause platform-specific issues)
    public void readStudentsFromFile(String filename) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(filename)); // DM_DEFAULT_ENCODING
        String line;
        while ((line = reader.readLine()) != null) {
            String[] data = line.split(",");
            addStudent(Integer.parseInt(data[0]), data[1], Double.parseDouble(data[2]));
        }
        reader.close();
    }

    // Generates random student ID (Bug: Inefficient use of Random inside loop)
    public int generateRandomStudentID() {
        return new Random().nextInt(1000); // DMI_RANDOM_USED_ONLY_ONCE
    }

    // Example of dead local store variable (Bug: Useless variable assignment)
    public void processStudents() {
        int x = 10; // DLS_DEAD_LOCAL_STORE (Assigned but never used)
    }

    public static void main(String[] args) {
        StudentManagement sm = new StudentManagement();
        sm.addStudent(1, "Alice", 3.8);
        sm.addStudent(2, "Bob", 2.9);

        sm.displayStudent(1);
        System.out.println("Average GPA: " + sm.calculateAverageGPA());
    }
}

// Separate Student class
class Student {
    int id;
    String name;
    double gpa;

    public Student(int id, String name, double gpa) {
        this.id = id;
        this.name = name;
        this.gpa = gpa;
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == this) return true;
        if (!(obj instanceof Student)) return false;
        Student other = (Student) obj;
        return this.id == other.id && name == obj.toString(); // EQ_ALWAYS_FALSE (Incorrect equals logic)
    }
}
