# Order Management: app quản lý đơn hàng (Frappe)

App Frappe nhỏ để quản lý đơn hàng. Mỗi đơn gồm khách hàng, mặt hàng, số lượng, đơn giá và thành tiền.

- Thành tiền do server tính.
- Trạng thái: Mới → Đã giao / Hủy. Đơn đã giao hoặc đã hủy thì bị khóa.
- Báo cáo doanh thu theo ngày.

Đã chạy thử trên **Frappe v15** và **MariaDB 10.11**.

## 1. Cài đặt

Yêu cầu: một bench Frappe **v15** (Python 3.10+, Node 18+, MariaDB, Redis). Nếu chưa có bench, xem [hướng dẫn cài Frappe](https://docs.frappe.io/framework/user/en/installation).

Chạy trong thư mục bench (thư mục tạo ra từ `bench init`):

```bash
bench get-app https://github.com/chanhchualam/chanhchualam
bench new-site order.local --admin-password admin --install-app order_management
bench use order.local
```

`bench new-site` sẽ hỏi mật khẩu root của MariaDB.

Nếu đã có site sẵn, chỉ cần cài thêm app:

```bash
bench --site <tên-site> install-app order_management
```

**Dữ liệu mẫu** (tùy chọn, nên chạy để xem nhanh):

```bash
bench --site order.local execute order_management.demo.setup_demo
```

Lệnh này tạo 8 khách hàng, 8 mặt hàng và 60 đơn rải trong 30 ngày gần nhất. Đơn được tạo qua `doc.insert()` / `doc.save()` nên đi qua đầy đủ các kiểm tra ở server. Nếu site chưa qua Setup Wizard, lệnh cũng tự hoàn tất bước này (Việt Nam, VND, Asia/Ho_Chi_Minh). Chạy lại lệnh không tạo trùng dữ liệu.

## 2. Chạy

```bash
bench start
```

Mở http://localhost:8000 và đăng nhập `Administrator` / `admin`.

| Việc | Cách làm |
|---|---|
| Trang chính | **Quản lý đơn hàng** ở thanh bên trái, có lối tắt: Tạo đơn mới, Đơn hàng, Doanh thu theo ngày, Khách hàng, Mặt hàng. |
| Tạo đơn | Lối tắt **Tạo đơn mới**, hoặc mở `/app/om-order/new`. Chọn khách hàng và mặt hàng (đơn giá tự điền theo mặt hàng, vẫn sửa được), nhập số lượng, rồi **Lưu** (Ctrl+S). Thành tiền do server tính. |
| Đổi trạng thái | Trên form đơn ở trạng thái Mới, bấm **Đổi trạng thái → Đã giao** hoặc **Hủy**. Sau đó form bị khóa. |
| Xem báo cáo | Lối tắt **Doanh thu theo ngày**, hoặc mở `/app/query-report/Daily Revenue`. Lọc theo khoảng ngày. |

Khách hàng (`OM Customer`) và mặt hàng (`OM Item`: mã số, tên, đơn giá) có thể tạo trước, hoặc tạo ngay trong ô chọn khi nhập đơn.

## 3. Test tự động

```bash
# Unit test quy tắc nghiệp vụ: không cần Frappe, chạy ở thư mục gốc repo
python -m unittest discover -s order_management/tests -t . -v

# Unit test + test tích hợp (tạo đơn, đổi trạng thái, khóa đơn, báo cáo): chạy trong thư mục bench
bench --site order.local set-config allow_tests true
bench --site order.local run-tests --app order_management
```

Kết quả: 32 test (14 unit + 18 tích hợp), tất cả đều qua.

## 4. Kiểm tra ở server

Mọi lần lưu `OM Order`, dù từ Desk, REST API hay code, đều đi qua `OMOrder.validate()`:

- Số lượng (số nguyên) và đơn giá phải lớn hơn 0. Để trống hoặc nhập số lẻ cho số lượng cũng bị từ chối.
- `amount` luôn được ghi lại bằng `qty × rate`. Giá trị client gửi lên bị bỏ qua.
- Đơn mới tạo phải ở trạng thái `Mới`. Gửi `Đã giao` ngay khi tạo sẽ bị từ chối.
- Chỉ cho phép chuyển `Mới → Đã giao` và `Mới → Hủy`.
- Đơn `Đã giao` hoặc `Hủy`: không sửa được khách hàng, mặt hàng, số lượng, đơn giá hay trạng thái, và không xóa được.
- Nếu hai người cùng sửa một đơn, Frappe so trường `modified` và báo lỗi `TimestampMismatchError` cho người lưu sau.

Giao diện (nút bấm, khóa form) chỉ giúp thao tác thuận tiện. Quy tắc thật nằm ở server.

## 5. Cấu trúc mã

| Tệp | Vai trò |
|---|---|
| `order_management/order_management/order_rules.py` | **Toàn bộ quy tắc nghiệp vụ**, không import frappe: kiểm tra số lượng và đơn giá, tính thành tiền, bảng chuyển trạng thái, khóa đơn |
| `…/doctype/om_order/om_order.py` | Controller: gọi `order_rules` trong `validate()` và `on_trash()` |
| `…/doctype/om_order/om_order.js` | Form: nút đổi trạng thái, khóa form khi đơn đã giao hoặc đã hủy |
| `…/report/daily_revenue/daily_revenue.py` | Báo cáo doanh thu theo ngày (Script Report, một câu SQL `GROUP BY DATE(creation)`) |
| `…/workspace/` | Trang "Quản lý đơn hàng" với lối tắt tới các màn hình (cài cùng app) |
| `order_management/demo.py` | Tạo dữ liệu mẫu |
| `order_management/install.py` | Chạy khi cài app: bật đồng VND và ký hiệu ₫ |
| `order_management/tests/test_order_rules.py` | Unit test |
| `…/doctype/om_order/test_om_order.py` | Test tích hợp |

## 6. Giả định

- Tên DocType có tiền tố `OM` (`OM Customer`, `OM Item`, `OM Order`) để không trùng `Customer` / `Item` của ERPNext nếu cài chung.
- Khách hàng chỉ có tên và số điện thoại. Mặt hàng có mã số (bắt buộc, không trùng, dùng làm mã của mặt hàng), tên và đơn giá. Chọn mặt hàng trong đơn thì đơn giá tự điền theo mặt hàng và vẫn sửa được. Gửi đơn qua API mà không có đơn giá thì server lấy giá của mặt hàng; gửi đơn giá 0 vẫn bị từ chối. Mỗi đơn lưu đơn giá riêng, nên đổi giá mặt hàng sau này không làm đổi đơn cũ.
- Số lượng là số nguyên (kiểu `Int`, hiện đúng `1` thay vì `1,000`). Tiền tệ là đồng Việt Nam (VND, ký hiệu ₫): đơn giá và thành tiền không có số lẻ, đơn giá nhập có số lẻ được làm tròn đến đồng (100,4 → 100). App tự bật VND khi cài (`install.py`).
- Không dùng cơ chế Submit/Cancel của Frappe. Trạng thái là trường `status` (Select), lưu thẳng chữ tiếng Việt `Mới` / `Đã giao` / `Hủy`.
- "Ngày tạo đơn" là trường hệ thống `creation`, tính theo múi giờ của site. Báo cáo không hiện những ngày không có đơn đã giao.
- Không cho xóa đơn đã giao hoặc đã hủy, vì tôi hiểu xóa cũng là một dạng sửa. Đơn `Mới` vẫn xóa được.
- Quyền truy cập: chỉ role `System Manager`.

## 7. Chưa làm / giới hạn

- Chưa có phân quyền theo vai trò (nhân viên bán hàng, kế toán…).
- `frappe.db.set_value()` hoặc SQL trực tiếp bỏ qua `validate()`. Đây là hành vi chuẩn của Frappe: quy tắc chỉ áp dụng cho các thao tác đi qua Document (Desk, REST API, `doc.save()`).
