# 性能优化指南

## 算法优化

### 时间复杂度分析

| 操作 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| 查找 | O(n) | O(1) | 使用哈希表 |
| 排序 | O(n²) | O(n log n) | 使用快速排序 |
| 搜索 | O(n) | O(log n) | 使用二分查找 |

### 数据结构选择

#### 数组 vs 链表
- **数组**：随机访问快，插入删除慢
- **链表**：插入删除快，随机访问慢

#### 哈希表
- 平均O(1)的查找、插入、删除
- 注意哈希冲突处理
- 考虑负载因子

#### 树结构
- 二叉搜索树：O(log n)操作
- 平衡树：AVL、红黑树
- B树：数据库索引

## 内存优化

### 对象池模式
```java
public class ObjectPool<T> {
    private final Queue<T> pool = new ConcurrentLinkedQueue<>();
    private final Supplier<T> factory;
    
    public ObjectPool(Supplier<T> factory) {
        this.factory = factory;
    }
    
    public T acquire() {
        T object = pool.poll();
        return object != null ? object : factory.get();
    }
    
    public void release(T object) {
        pool.offer(object);
    }
}
```

### 内存映射文件
- 处理大文件时使用
- 减少内存占用
- 提高I/O性能

### 弱引用和软引用
- WeakReference：GC时立即回收
- SoftReference：内存不足时回收
- 适用于缓存场景

## I/O优化

### 缓冲区优化
```java
// 错误示例：逐字节读取
int data;
while ((data = inputStream.read()) != -1) {
    // 处理单个字节
}

// 正确示例：使用缓冲区
byte[] buffer = new byte[8192];
int bytesRead;
while ((bytesRead = inputStream.read(buffer)) != -1) {
    // 处理缓冲区数据
}
```

### 异步I/O
- 使用NIO或异步框架
- 避免阻塞线程
- 提高并发性能

### 批量操作
- 批量数据库操作
- 批量文件操作
- 减少网络往返

## 并发优化

### 线程池配置
```java
// CPU密集型任务
int cpuCount = Runtime.getRuntime().availableProcessors();
ExecutorService cpuPool = Executors.newFixedThreadPool(cpuCount);

// I/O密集型任务
ExecutorService ioPool = Executors.newCachedThreadPool();
```

### 无锁编程
- 使用原子类
- CAS操作
- volatile关键字

### 并发集合
- ConcurrentHashMap
- CopyOnWriteArrayList
- BlockingQueue

## 数据库优化

### 索引策略
- 为WHERE条件创建索引
- 复合索引的顺序很重要
- 避免过度索引

### 查询优化
- 使用EXPLAIN分析查询
- 避免SELECT *
- 合理使用JOIN

### 连接池
- 配置合适的连接数
- 设置超时时间
- 监控连接使用情况