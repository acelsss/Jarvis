# 常见代码问题模式

## Bug模式

### 空指针引用
```java
// 错误示例
if (user != null && user.getName().equals("admin")) {
    // 处理逻辑
}

// 正确示例
if (user != null) {
    String name = user.getName();
    if (name != null && name.equals("admin")) {
        // 处理逻辑
    }
}
```

### 资源泄漏
```python
# 错误示例
file = open("data.txt")
data = file.read()
# 忘记关闭文件

# 正确示例
with open("data.txt") as file:
    data = file.read()
# 自动关闭文件
```

### 竞态条件
```javascript
// 错误示例
let counter = 0;
function increment() {
    counter++; // 非原子操作
}

// 正确示例
let counter = 0;
const mutex = new Mutex();
async function increment() {
    const release = await mutex.acquire();
    try {
        counter++;
    } finally {
        release();
    }
}
```

## 性能问题

### N+1查询问题
```sql
-- 错误示例：在循环中执行查询
SELECT * FROM users;
-- 对于每个用户，执行：
SELECT * FROM orders WHERE user_id = ?;

-- 正确示例：使用JOIN
SELECT u.*, o.* FROM users u 
LEFT JOIN orders o ON u.id = o.user_id;
```

### 内存泄漏
```java
// 错误示例：静态集合持有对象引用
public class Cache {
    private static final Map<String, Object> cache = new HashMap<>();
    
    public void addToCache(String key, Object value) {
        cache.put(key, value); // 永远不会清理
    }
}

// 正确示例：使用WeakHashMap或设置过期时间
public class Cache {
    private static final Map<String, Object> cache = new WeakHashMap<>();
    
    public void addToCache(String key, Object value) {
        cache.put(key, value);
    }
}
```

## 安全问题

### SQL注入
```php
// 错误示例
$query = "SELECT * FROM users WHERE id = " . $_GET['id'];

// 正确示例：使用预处理语句
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");
$stmt->execute([$_GET['id']]);
```

### XSS攻击
```javascript
// 错误示例
document.getElementById('output').innerHTML = userInput;

// 正确示例：转义用户输入
document.getElementById('output').textContent = userInput;
```

## 代码异味

### 长方法
- 方法超过50行
- 包含多个职责
- 难以理解和测试

### 大类
- 类超过500行
- 包含太多方法和属性
- 违反单一职责原则

### 重复代码
- 相同或相似的代码片段
- 复制粘贴的逻辑
- 应该提取为公共方法