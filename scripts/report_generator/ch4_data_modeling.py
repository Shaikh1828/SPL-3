"""
Chapter 4: Data-Based Modeling Module for Bull's Eye SPL-3 Final Technical Report.
Covers 3NF Entity Relationship Diagram (ERD), Normalization Rationale (1NF, 2NF, 3NF),
and Comprehensive Data Dictionary for all 8 Relational Entities.
"""

def get_chapter_4():
    return r"""---

# CHAPTER 4: DATA-BASED MODELING

## 4.1 3NF Entity Relationship Diagram (ERD) & Normalization Rationale

Data-based modeling establishes the logical and physical schema governing all persistent states in Bull's Eye. To ensure transactional integrity, eliminate insertion, update, and deletion anomalies, and support sub-millisecond query execution, the database schema was designed in strict accordance with Third Normal Form (3NF).

### 4.1.1 Normalization Rationale
1. **First Normal Form (1NF)**:
   - All attribute values are strictly atomic. Multivalued attributes, such as arrow coordinates, are broken down into discrete Cartesian floats (`x_coordinate`, `y_coordinate`, `radial_distance`).
   - Every relation possesses a distinct Primary Key (UUID or auto-incrementing integer).
   - No repeating groups exist across tables; multiple arrows per end are modeled as discrete rows in the `scores` table rather than an array column.
2. **Second Normal Form (2NF)**:
   - The schema satisfies 1NF.
   - All non-key attributes are fully functionally dependent on the entire primary key. In composite junction tables, such as `session_archers` (composite PK: `session_id`, `user_id`), attributes like `lane_number` and `target_number` depend on the specific assignment pair, with no partial dependencies.
3. **Third Normal Form (3NF)**:
   - The schema satisfies 2NF.
   - All transitive functional dependencies ($X \to Y \to Z$) have been eliminated. For example, tournament metadata (`tournament_name`, `target_face_type`) is not stored within the `scores` or `sessions` tables; `scores` references `session_id`, which references `tournament_id`. Archer biographical details are isolated in `users`, preventing redundant duplication across multiple matches.

```
+----------------------------------------------------------------------------------------------------+
|                         THIRD NORMAL FORM (3NF) ENTITY RELATIONSHIP DIAGRAM                        |
|                                                                                                    |
|    +----------------------+                    +-----------------------+                           |
|    |        USERS         |                    |      TOURNAMENTS      |                           |
|    +----------------------+                    +-----------------------+                           |
|    | PK id                |<-----+             | PK id                 |<-------+                  |
|    |    email (UQ)        |      |             |    name               |        |                  |
|    |    hashed_password   |      |             |    target_face_type   |        |                  |
|    |    role              |      |             |    total_ends         |        |                  |
|    |    full_name         |      |             |    arrows_per_end     |        |                  |
|    |    created_at        |      |             |    created_by (FK)----+        |                  |
|    +----------------------+      |             |    created_at         |        |                  |
|              ^                   |             +-----------------------+        |                  |
|              | 1:N               |                         ^                    |                  |
|              |                   |                         | 1:N                |                  |
|    +----------------------+      |             +-----------------------+        |                  |
|    |   SESSION_ARCHERS    |      |             |       SESSIONS        |        |                  |
|    +----------------------+      |             +-----------------------+        |                  |
|    | PK session_id (FK)---+------+-------------+>PK id                 |        |                  |
|    | PK user_id (FK)------+      |             |    tournament_id (FK)-+--------+                  |
|    |    lane_number       |      |             |    status             |                           |
|    |    target_number     |      |             |    current_end        |                           |
|    |    created_at        |      |             |    started_at         |                           |
|    +----------------------+      |             +-----------------------+                           |
|              ^                   |                         ^                                       |
|              | 1:N               |                         | 1:N                                   |
|              |                   |                         |                                       |
|    +----------------------+      |             +-----------------------+                           |
|    |        SCORES        |      |             |       CAMERAS         |                           |
|    +----------------------+      |             +-----------------------+                           |
|    | PK id                |      |             | PK id                 |<-------+                  |
|    | FK session_id        +------+             |    name               |        |                  |
|    | FK archer_id         |                    |    stream_url         |        |                  |
|    |    end_number        |                    |    is_active          |        |                  |
|    |    arrow_number      |                    |    calibration_matrix |        |                  |
|    |    score_value       |                    |    created_at         |        |                  |
|    |    is_x_ring         |                    +-----------------------+        |                  |
|    |    x_coordinate      |                                ^                    |                  |
|    |    y_coordinate      |                                | 1:N                |                  |
|    |    radial_distance   |                    +-----------------------+        |                  |
|    |    confidence        |                    |CAMERA_LANE_ASSIGNMENTS|        |                  |
|    |    is_manual_override|                    +-----------------------+        |                  |
|    |    created_at        |                    | PK id                 |        |                  |
|    +----------------------+                    | FK session_id         |        |                  |
|              ^                                 | FK camera_id ---------+--------+                  |
|              | 1:N                             |    lane_number        |                           |
|    +----------------------+                    |    assigned_at        |                           |
|    |      AUDIT_LOGS      |                    +-----------------------+                           |
|    +----------------------+                                                                        |
|    | PK id                |                                                                        |
|    | FK score_id ---------+                                                                        |
|    | FK judge_id ---------+ (Points to USERS.id)                                                   |
|    |    original_score    |                                                                        |
|    |    new_score         |                                                                        |
|    |    override_reason   |                                                                        |
|    |    created_at        |                                                                        |
|    +----------------------+                                                                        |
+----------------------------------------------------------------------------------------------------+
```
*Figure 4.1: Third Normal Form (3NF) Entity Relationship Diagram (ERD)*

## 4.2 Comprehensive Data Dictionary

The data dictionary provides the exact schema definition, data types, constraints, foreign key relationships, and functional descriptions for all eight relational entities implemented in the PostgreSQL database.

### 4.2.1 Table: `users`
*Table 4.1: Data Dictionary: `users` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique system-wide identifier for user. |
| `email` | `VARCHAR(255)` | No | UNIQUE, INDEX | - | User login email address; normalized lowercase. |
| `hashed_password` | `VARCHAR(255)` | No | - | - | Bcrypt-hashed password salt and digest. |
| `full_name` | `VARCHAR(100)` | No | - | - | Legal name of competitor, judge, or admin. |
| `role` | `VARCHAR(30)` | No | CHECK (`role IN ('admin', 'scorer', 'archer')`) | - | Role-based authorization principal. |
| `is_active` | `BOOLEAN` | No | DEFAULT `TRUE` | - | Account active status flag for soft deactivation. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | System creation audit timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Last modification timestamp. |

---

### 4.2.2 Table: `tournaments`
*Table 4.2: Data Dictionary: `tournaments` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique identifier for tournament. |
| `name` | `VARCHAR(150)` | No | INDEX | - | Competition title (e.g., "National Championship"). |
| `target_face_type` | `VARCHAR(50)` | No | DEFAULT `'WA_122CM'` | - | World Archery face standard (`WA_122CM`, `WA_80CM`). |
| `total_ends` | `INTEGER` | No | CHECK (`total_ends > 0`), DEFAULT `12` | - | Number of regulation ends in competition. |
| `arrows_per_end` | `INTEGER` | No | CHECK (`arrows_per_end > 0`), DEFAULT `6` | - | Number of arrows allocated per end. |
| `status` | `VARCHAR(30)` | No | DEFAULT `'SCHEDULED'` | - | Lifecycle state: `SCHEDULED`, `ACTIVE`, `COMPLETED`. |
| `created_by` | `UUID` | No | FK | `users(id)` | User ID of the administrator who created tournament. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Record creation timestamp. |

---

### 4.2.3 Table: `sessions`
*Table 4.3: Data Dictionary: `sessions` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique match session identifier. |
| `tournament_id` | `UUID` | No | FK, INDEX | `tournaments(id)` | Parent tournament foreign key (CASCADE on delete). |
| `status` | `VARCHAR(30)` | No | DEFAULT `'INITIALIZED'` | - | State: `INITIALIZED`, `ACTIVE`, `PAUSED`, `FINISHED`. |
| `current_end` | `INTEGER` | No | DEFAULT `1` | - | Active competition end being scored. |
| `started_at` | `TIMESTAMPTZ` | Yes | - | - | Official match start timestamp. |
| `ended_at` | `TIMESTAMPTZ` | Yes | - | - | Official match conclusion timestamp. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Record creation timestamp. |

---

### 4.2.4 Table: `session_archers`
*Table 4.4: Data Dictionary: `session_archers` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `session_id` | `UUID` | No | PK, FK | `sessions(id)` | Associated session foreign key. |
| `user_id` | `UUID` | No | PK, FK | `users(id)` | Assigned archer foreign key. |
| `lane_number` | `INTEGER` | No | CHECK (`lane_number > 0`) | - | Assigned physical shooting lane (1..N). |
| `target_number` | `VARCHAR(10)` | No | DEFAULT `'A'` | - | Target position identifier (e.g., 'A', 'B', 'C'). |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Assignment timestamp. |

---

### 4.2.5 Table: `scores`
*Table 4.5: Data Dictionary: `scores` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique arrow score record identifier. |
| `session_id` | `UUID` | No | FK, INDEX | `sessions(id)` | Match session foreign key. |
| `archer_id` | `UUID` | No | FK, INDEX | `users(id)` | Archer who shot the arrow. |
| `end_number` | `INTEGER` | No | CHECK (`end_number >= 1`) | - | Competition end index (1..12). |
| `arrow_number` | `INTEGER` | No | CHECK (`arrow_number >= 1`) | - | Sequential arrow index within the end (1..6). |
| `score_value` | `INTEGER` | No | CHECK (`score_value BETWEEN 0 AND 10`) | - | Points awarded (0 for Miss, 1 to 10). |
| `is_x_ring` | `BOOLEAN` | No | DEFAULT `FALSE` | - | True if arrow hit within Inner-10 (X) boundary. |
| `x_coordinate` | `DOUBLE PRECISION`| No | - | - | Rectified planar X offset from center (mm or normalized). |
| `y_coordinate` | `DOUBLE PRECISION`| No | - | - | Rectified planar Y offset from center (mm or normalized). |
| `radial_distance`| `DOUBLE PRECISION`| No | - | - | Euclidean distance $r = \sqrt{x^2+y^2}$ from target center. |
| `confidence` | `DOUBLE PRECISION`| No | DEFAULT `1.0` | - | Algorithmic consensus detection confidence (0.0 to 1.0).|
| `detection_method`| `VARCHAR(50)`| No | DEFAULT `'HYBRID'` | - | Detection method used (`MORPHOLOGY`, `YOLO`, `MANUAL`). |
| `is_manual_override`|`BOOLEAN` | No | DEFAULT `FALSE` | - | Flag indicating judicial human override. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Shot timestamp. |

---

### 4.2.6 Table: `cameras`
*Table 4.6: Data Dictionary: `cameras` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique camera hardware identifier. |
| `name` | `VARCHAR(100)` | No | - | - | Human-readable camera label (e.g., "Lane 1 Target Cam"). |
| `stream_url` | `VARCHAR(255)` | No | - | - | RTSP, HTTP, or device index URL (`rtsp://192.168.1.100`).|
| `is_active` | `BOOLEAN` | No | DEFAULT `TRUE` | - | Hardware stream operational status. |
| `calibration_matrix`| `JSONB` | Yes | - | - | 9-element 3x3 perspective homography matrix array. |
| `last_ping` | `TIMESTAMPTZ` | Yes | - | - | Timestamp of most recent successful healthcheck ping. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Record creation timestamp. |

---

### 4.2.7 Table: `camera_lane_assignments`
*Table 4.7: Data Dictionary: `camera_lane_assignments` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique assignment record identifier. |
| `session_id` | `UUID` | No | FK, INDEX | `sessions(id)` | Session foreign key. |
| `camera_id` | `UUID` | No | FK | `cameras(id)` | Camera hardware foreign key. |
| `lane_number` | `INTEGER` | No | CHECK (`lane_number > 0`) | - | Assigned physical shooting lane index. |
| `assigned_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Timestamp when assignment was provisioned. |

---

### 4.2.8 Table: `audit_logs`
*Table 4.8: Data Dictionary: `audit_logs` Relational Entity*

| Column Name | Data Type | Nullable | Constraints | Reference | Functional Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | No | PK, `gen_random_uuid()` | - | Unique audit log entry identifier. |
| `score_id` | `UUID` | No | FK, INDEX | `scores(id)` | Target score record modified. |
| `judge_id` | `UUID` | No | FK, INDEX | `users(id)` | User ID of the line judge executing the override. |
| `original_score` | `INTEGER` | No | - | - | Algorithmic score value prior to modification (0..10). |
| `new_score` | `INTEGER` | No | - | - | Overridden score value awarded by judge (0..10). |
| `original_x_ring` | `BOOLEAN` | No | - | - | Original X-ring status before modification. |
| `new_x_ring` | `BOOLEAN` | No | - | - | Overridden X-ring status awarded by judge. |
| `override_reason` | `TEXT` | No | - | - | Mandatory judicial rationale explaining the decision. |
| `created_at` | `TIMESTAMPTZ` | No | DEFAULT `NOW()` | - | Cryptographic timestamp of judicial action. |
"""
