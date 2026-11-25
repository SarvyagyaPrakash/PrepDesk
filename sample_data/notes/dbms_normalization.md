# DBMS Normalization (1NF, 2NF, 3NF, BCNF)

Database normalization is the process of organizing tables and columns in a relational database to minimize data redundancy and prevent update, insertion, and deletion anomalies.

## Core Definitions

- **Functional Dependency ($X \to Y$):** An attribute set $X$ uniquely determines attribute set $Y$ if any two rows with the same $X$ values must also have the same $Y$ values.
- **Candidate Key:** A minimal set of attributes that uniquely identifies every tuple in a relation.
- **Prime Attribute:** Any attribute that belongs to at least one candidate key.

## Normal Forms

1. **First Normal Form (1NF):**
   - Every column holds atomic (indivisible) values, and there are no repeating groups or nested arrays.
2. **Second Normal Form (2NF):**
   - The table is in 1NF, and **no non-prime attribute is partially dependent** on part of a composite candidate key.
   - Single-attribute primary key tables in 1NF are automatically in 2NF.
3. **Third Normal Form (3NF):**
   - The table is in 2NF, and **no non-prime attribute is transitively dependent** on a candidate key (i.e., for every $X \to A$, either $X$ is a superkey or $A$ is a prime attribute).
4. **Boyce-Codd Normal Form (BCNF):**
   - For every non-trivial functional dependency $X \to Y$, $X$ must be a **superkey**. BCNF is strictly stronger than 3NF and eliminates anomalies caused by overlapping candidate keys.

## Worked Example

Consider a table `CourseEnrollment(StudentID, CourseID, StudentName, Instructor, Room)` with primary key `(StudentID, CourseID)` and dependencies:
- `StudentID -> StudentName`
- `CourseID -> Instructor, Room`
- `Instructor -> Room`

**Step 1 (Check 2NF):** `StudentName` depends only on `StudentID` (partial dependency), and `Instructor, Room` depend only on `CourseID`. Decompose into:
- `Students(StudentID, StudentName)`
- `Courses(CourseID, Instructor, Room)`
- `Enrollments(StudentID, CourseID)`

**Step 2 (Check 3NF):** In `Courses`, `CourseID -> Instructor` and `Instructor -> Room` create a transitive dependency (`CourseID -> Room` via `Instructor`). Decompose `Courses` further into:
- `Courses(CourseID, Instructor)`
- `Instructors(Instructor, Room)`

Now every table is in 3NF and BCNF: changing an instructor's room requires updating only one row in `Instructors`, deleting an enrollment never erases course metadata, and adding a new instructor does not require a dummy course.
