from datetime import datetime
from enum import Enum, IntFlag, auto

from sqlalchemy import Table, Column, Integer, String, Text, LargeBinary, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_fulltext import FullText
from sqlalchemy_utils import ChoiceType

Base = declarative_base()

# convert collations
@compiles(String, 'postgresql')
def compile_unicode(element, compiler, **kw):
    if element.collation == 'NOCASE':
        element.collation = 'und-x-icu'
    return compiler.visit_unicode(element, **kw)
@compiles(Text, 'postgresql')
def compile_unicode(element, compiler, **kw):
    if element.collation == 'NOCASE':
        element.collation = 'und-x-icu'
    return compiler.visit_unicode(element, **kw)


class FlagProperty:
    def __init__(self, attr, flag):
        self.attr = attr
        self.flag = flag
    
    def __get__(self, obj, cls):
        return bool(getattr(obj, self.attr) & self.flag)
    
    def __set__(self, obj, value):
        setattr(obj, self.attr, (getattr(obj, self.attr) & ~self.flag) | (-bool(value) & self.flag))


post_tag = Table('post_tag', Base.metadata,
    Column('post_id', Integer, ForeignKey('post.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('tag_id', Integer, ForeignKey('tag.id', ondelete='CASCADE'), nullable=False)
)

class TagCategory(Enum):
    general = 1
    group = 2
    artist = 3
    copyright = 4
    character = 5
    # used for informational tags or personal reminders
    meta = 6

class TagFlags(IntFlag):
    none = 0
    favorite = auto()

class Tag(Base):
    __tablename__ = 'tag'
    
    id = Column(Integer, primary_key=True)
    
    category = Column(ChoiceType(TagCategory, impl=Integer()), nullable=False)
    tag = Column(String(length=255, collation='NOCASE'), nullable=False)
    
    flags = Column(Integer, default=TagFlags.none, nullable=False)
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # flags
    favorite = FlagProperty('flags', TagFlags.favorite)
    
    __table_args__ = (
        Index('idx_tags', 'category', 'tag', unique=True),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = TagFlags.none
    
    def __str__(self):
        return '{}:{}'.format(self.category.name, self.tag)

class PostFlags(IntFlag):
    none = 0
    favorite = auto()
    hidden = auto()
    removed = auto() # if the post was deleted in the remote host

class PostType(Enum):
    set = 1 # bundle of unrelated files (or just a single file)
    collection = 2 # the files are related in some way
    blog = 3 # text with files in between (comment is formatted as json)
    # more types can be added as needed

class Post(Base):
    __tablename__ = 'post'
    
    id = Column(Integer, primary_key=True)
    
    title = Column(Text(collation='NOCASE'))
    comment = Column(Text(collation='NOCASE'))
    
    type = Column(ChoiceType(PostType, impl=Integer()), nullable=False)
    flags = Column(Integer, default=PostFlags.none, nullable=False)
    
    metadata_ = Column('metadata', Text)
    post_time = Column(DateTime(timezone=False))
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    tags = relationship('Tag', secondary=post_tag)
    files = relationship('File', back_populates='local')
    
    # flags
    favorite = FlagProperty('flags', PostFlags.favorite)
    hidden = FlagProperty('flags', PostFlags.hidden)
    removed = FlagProperty('flags', PostFlags.removed)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = PostFlags.none


class Source(Base):
    __tablename__ = 'source'
    
    id = Column(Integer, primary_key=True)
    
    name = Column(String(length=255, collation='NOCASE'), nullable=False, index=True, unique=True)
    version = Column(Integer, nullable=False)
    config = Column(Text)
    
    metadata_ = Column('metadata', Text)
    
    hoordu_config = Column(Text)
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    subscriptions = relationship('Subscription', back_populates='source')

remote_post_tag = Table('remote_post_tag', Base.metadata,
    Column('post_id', Integer, ForeignKey('remote_post.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('tag_id', Integer, ForeignKey('remote_tag.id', ondelete='CASCADE'), nullable=False)
)

class RemoteTag(Base):
    __tablename__ = 'remote_tag'
    
    id = Column(Integer, primary_key=True)
    
    source_id = Column(Integer, ForeignKey('source.id', ondelete='CASCADE'), nullable=False)
    
    category = Column(ChoiceType(TagCategory, impl=Integer()), nullable=False)
    tag = Column(String(length=255, collation='NOCASE'), nullable=False)
    
    metadata_ = Column('metadata', Text)
    
    flags = Column(Integer, default=TagFlags.none, nullable=False)
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    source = relationship('Source')
    translation = relationship('TagTranslation', back_populates='remote_tag')
    
    # flags
    favorite = FlagProperty('flags', TagFlags.favorite)
    
    __table_args__ = (
        Index('idx_remote_tags', 'source_id', 'category', 'tag', unique=True),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = TagFlags.none
    
    def __str__(self):
        return '{}:{}'.format(self.category.name, self.tag)

class RemotePost(Base):
    __tablename__ = 'remote_post'
    
    id = Column(Integer, primary_key=True)
    
    source_id = Column(Integer, ForeignKey('source.id', ondelete='CASCADE'), nullable=False)
    
    # the minimum identifier for the post
    original_id = Column(Text, nullable=False)
    url = Column(Text)
    
    title = Column(Text(collation='NOCASE'))
    comment = Column(Text(collation='NOCASE'))
    
    type = Column(ChoiceType(PostType, impl=Integer()), nullable=False)
    flags = Column(Integer, default=PostFlags.none, nullable=False)
    
    metadata_ = Column('metadata', Text)
    post_time = Column(DateTime(timezone=False))
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    source = relationship('Source')
    tags = relationship('RemoteTag', secondary=remote_post_tag)
    files = relationship('File', back_populates='remote')
    related = relationship('Related', back_populates='related_to', foreign_keys='[Related.related_to_id]')
    
    # flags
    favorite = FlagProperty('flags', PostFlags.favorite)
    hidden = FlagProperty('flags', PostFlags.hidden)
    removed = FlagProperty('flags', PostFlags.removed)
    
    __table_args__ = (
        Index('idx_remote_posts', 'source_id', 'original_id', unique=True),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = PostFlags.none


class FileFlags(IntFlag):
    none = 0
    favorite = auto()
    hidden = auto()
    removed = auto() # if the file was removed in the remote host
    processed = auto() # if the file was already processed locally (accepted or rejected)
    present = auto() # if the file is present on the disk
    thumb_present = auto() # if the thumbnail is present on the disk

class File(Base):
    __tablename__ = 'file'
    
    id = Column(Integer, primary_key=True)
    
    local_id = Column(Integer, ForeignKey('post.id', ondelete='SET NULL'))
    remote_id = Column(Integer, ForeignKey('remote_post.id', ondelete='SET NULL'))
    
    local_order = Column(Integer, default=0)
    remote_order = Column(Integer, default=0)
    
    # hash is md5 for compatibility
    hash = Column(LargeBinary(length=16), index=True)
    filename = Column(Text)
    mime = Column(String(length=255, collation='NOCASE'))
    ext = Column(String(length=20, collation='NOCASE'))
    thumb_ext = Column(String(length=20, collation='NOCASE'))
    
    metadata_ = Column('metadata', Text)
    
    flags = Column(Integer, default=FileFlags.none, nullable=False)
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    local = relationship('Post', back_populates='files')
    remote = relationship('RemotePost', back_populates='files')
    
    # flags
    favorite = FlagProperty('flags', FileFlags.favorite)
    hidden = FlagProperty('flags', FileFlags.hidden)
    removed = FlagProperty('flags', FileFlags.removed)
    processed = FlagProperty('flags', FileFlags.processed)
    present = FlagProperty('flags', FileFlags.present)
    thumb_present = FlagProperty('flags', FileFlags.thumb_present)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = FileFlags.none


subscription_post = Table('feed', Base.metadata,
    Column('subscription_id', Integer, ForeignKey('subscription.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('remote_post_id', Integer, ForeignKey('remote_post.id', ondelete='CASCADE'), nullable=False)
)

class SubscriptionFlags(IntFlag):
    none = 0
    enabled = auto() # won't auto update if disabled

class Subscription(Base):
    __tablename__ = 'subscription'
    
    id = Column(Integer, primary_key=True)
    
    source_id = Column(Integer, ForeignKey('source.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(Text, nullable=False)
    
    options = Column(Text)
    state = Column(Text)
    
    flags = Column(Integer, default=SubscriptionFlags.none, nullable=False)
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    source = relationship('Source', back_populates='subscriptions')
    feed = relationship('RemotePost', secondary=subscription_post)
    
    # flags
    enabled = FlagProperty('flags', SubscriptionFlags.enabled)
    
    __table_args__ = (
        Index('idx_subscription', 'source_id', 'name', unique=True),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'flags' not in kwargs:
            self.flags = SubscriptionFlags.enabled


class TagTranslation(Base):
    __tablename__ = 'tag_translation'
    
    id = Column(Integer, ForeignKey('remote_tag.id', ondelete='CASCADE'), primary_key=True)
    # null local_tag_id -> ignore remote tag
    local_tag_id = Column(Integer, ForeignKey('tag.id', ondelete='CASCADE'))
    
    created_time = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_time = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # references
    remote_tag = relationship('RemoteTag', back_populates='translation')
    tag = relationship('Tag')

class Related(Base):
    __tablename__ = 'related'
    
    id = Column(Integer, primary_key=True)
    # the post this url is related to
    related_to_id = Column(Integer, ForeignKey('remote_post.id', ondelete='CASCADE'))
    
    # the post the url corresponds to, in case it was downloaded
    remote_id = Column(Integer, ForeignKey('remote_post.id', ondelete='SET NULL'))
    
    url = Column(Text)
    
    related_to = relationship('RemotePost', back_populates='related', foreign_keys=[related_to_id])
    remote = relationship('RemotePost', foreign_keys=[remote_id])


