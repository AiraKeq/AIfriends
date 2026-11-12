def remove_old_photo(photo):
    """删除旧上传文件，保留字段默认图片，不改动模型中的新图片引用。"""
    if not photo or not photo.name:
        return

    # 默认图片可能被多个用户共用，不能删除。
    if photo.name == photo.field.get_default():
        return

    # 使用 Django storage 的路径校验与删除，不拼接未经校验的磁盘路径。
    photo.storage.delete(photo.name)
