import java.util.ArrayList;
import java.util.List;

public class UserAccountManager {

    private List<String> users = new ArrayList<>();

    public void addUser(String username) {
        if (username == null) {
            return;  // PMD will catch: AvoidReturningFromCatchFinallyBlock / EmptyIfStmt
        }

        if (users.contains(username)) {
            System.out.println("User already exists");
        }

        users.add(username);  // PMD: add anyway even if user exists (bad practice)
    }

    public void removeUser(String username) {
        // PMD: Possible NPE because no null check on username
        users.remove(username);
    }

    public void printUsers() {
        for (int i = 0; i <= users.size(); i++) {  // PMD: ArrayIndexOutOfBounds
            System.out.println(users.get(i));
        }
    }

    public void insecurePasswordHandling(String password) {
        // PMD Security: Hardcoded password pattern
        String defaultPassword = "password123";

        if (password.equals(defaultPassword)) {  // PMD: .equals() on hardcoded value
            System.out.println("Default password is insecure!");
        }
    }

    public static void main(String[] args) {
        UserAccountManager manager = new UserAccountManager();

        manager.addUser("alice");
        manager.addUser("bob");
        manager.addUser("alice");  // Duplicate user

        manager.removeUser(null);  // PMD: Possible NullPointerException

        manager.printUsers();

        manager.insecurePasswordHandling("password123");  // PMD Security Issue
    }
}
