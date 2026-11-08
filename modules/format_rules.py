class FormatRules:
    DOC_FORMATS = ['docx', 'odt', 'rtf', 'txt', 'md', 'html']
    IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'ico', 'heic', 'heif']
    AUDIO_FORMATS = ['wav', 'mp3', 'flac', 'aac', 'ogg', 'm4a', 'opus', 'wma']
    VIDEO_FORMATS = ['mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'mpg', 'mpeg']

    @staticmethod
    def get_category(ext):
        ext = ext.lower().replace('.', '')
        if ext in FormatRules.DOC_FORMATS:
            return 'document'
        if ext in FormatRules.IMAGE_FORMATS:
            return 'image'
        if ext in FormatRules.AUDIO_FORMATS:
            return 'audio'
        if ext in FormatRules.VIDEO_FORMATS:
            return 'video'
        return 'unknown'

    @staticmethod
    def get_target_formats(input_ext):
        # Import here to avoid circular dependency at module level if ConfigManager imports FormatRules
        from .config_manager import ConfigManager
        advanced = ConfigManager().get("enable_advanced_formats")

        ext = input_ext.lower().lstrip('.')
        category = FormatRules.get_category(ext)

        doc_std = ['pdf', 'docx', 'odt', 'rtf', 'txt', 'md', 'html']
        img_std = ['jpg', 'png', 'webp', 'tiff', 'ico', 'heic', 'pdf']

        audio_std = ['mp3', 'wav', 'aac', 'ogg', 'm4a', 'flac']
        audio_adv = audio_std + ['opus', 'wma', 'amr']

        video_std = ['mp4', 'mkv', 'webm']
        video_adv = video_std + ['avi', 'mov', 'flv', 'wmv', '3gp', 'mpg']
        # Video files can also be turned into audio (extract soundtrack) or a GIF
        video_extra = ['mp3', 'wav', 'm4a', 'gif']

        if ext == 'pdf':
            # PDF can go to Doc formats AND Image formats
            return [f for f in doc_std + img_std if f != 'pdf']
        if category == 'document':
            return list(doc_std)
        if category == 'image':
            return list(img_std)
        if category == 'audio':
            return list(audio_adv if advanced else audio_std)
        if category == 'video':
            return (video_adv if advanced else video_std) + video_extra
        return []
